from typing import Dict, List, Optional
import logging
from datetime import datetime
from langchain.prompts import PromptTemplate
from .rag import EnhancedRAGSystem
from .models import Tweet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import json

logger = logging.getLogger(__name__)

CONTENT_OPTIMIZATION_PROMPT = """Analyze and optimize this content for {platform}.

Content: {content}

Consider:
1. Platform-specific best practices
2. Engagement potential
3. Clarity and impact
4. Call to action effectiveness

Previous performance data:
{performance_data}

Provide specific suggestions for:
1. Content structure
2. Engagement elements
3. Timing and frequency
4. Keywords and hashtags

Response should be in JSON format with these keys:
- improved_content
- suggestions
- engagement_score (0-100)
- best_time_to_post
- hashtags
- keywords
"""

class ContentAdvisor:
    def __init__(self, rag_system: EnhancedRAGSystem, db_session: AsyncSession):
        """Initialize Content Advisor with RAG system and database session"""
        self.rag = rag_system
        self.db = db_session
        self.prompt = PromptTemplate(
            template=CONTENT_OPTIMIZATION_PROMPT,
            input_variables=["platform", "content", "performance_data"]
        )
        self.performance_cache = {}

    async def optimize_content(
        self,
        content: str,
        platform: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Optimize content for specific platform using RAG and performance data
        Returns optimized content and suggestions
        """
        try:
            # Get performance data for similar content
            performance_data = await self._get_performance_data(content, platform)
            
            # Prepare optimization prompt
            optimization_input = {
                "platform": platform,
                "content": content,
                "performance_data": json.dumps(performance_data)
            }
            
            # Get optimization suggestions from RAG
            result = await self.rag.query(
                self.prompt.format(**optimization_input),
                confidence_threshold=0.8
            )
            
            # Parse RAG response
            try:
                suggestions = json.loads(result["answer"])
            except json.JSONDecodeError:
                logger.error("Failed to parse RAG response as JSON")
                suggestions = {
                    "improved_content": content,
                    "suggestions": ["Error processing suggestions"],
                    "engagement_score": 0,
                    "best_time_to_post": "N/A",
                    "hashtags": [],
                    "keywords": []
                }
            
            # Add platform-specific optimizations
            if platform == "twitter":
                suggestions.update(await self._optimize_for_twitter(content))
            elif platform == "telegram":
                suggestions.update(await self._optimize_for_telegram(content))
            
            return {
                "status": "success",
                "original_content": content,
                "optimized_content": suggestions["improved_content"],
                "suggestions": suggestions["suggestions"],
                "metrics": {
                    "engagement_score": suggestions["engagement_score"],
                    "best_time": suggestions["best_time_to_post"],
                    "confidence": result["confidence"]
                },
                "tags": {
                    "hashtags": suggestions["hashtags"],
                    "keywords": suggestions["keywords"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error optimizing content: {e}")
            return {
                "status": "error",
                "message": "Failed to optimize content",
                "error": str(e)
            }

    async def _optimize_for_twitter(self, content: str) -> Dict:
        """Twitter-specific optimizations"""
        suggestions = {
            "character_count": len(content),
            "media_suggestions": []
        }
        
        # Character count optimization
        if len(content) > 280:
            suggestions["suggestions"] = [
                "Content exceeds Twitter's 280 character limit",
                "Consider breaking into multiple tweets"
            ]
        
        # Media and link suggestions
        if "http" in content:
            suggestions["media_suggestions"].append(
                "Consider adding preview cards for links"
            )
        
        return suggestions

    async def _optimize_for_telegram(self, content: str) -> Dict:
        """Telegram-specific optimizations"""
        suggestions = {
            "formatting_suggestions": [],
            "media_suggestions": []
        }
        
        # Formatting suggestions
        if len(content.split('\n')) < 3:
            suggestions["formatting_suggestions"].append(
                "Consider adding line breaks for better readability"
            )
        
        # Media suggestions
        if len(content) > 300 and not "http" in content:
            suggestions["media_suggestions"].append(
                "Consider adding visual elements for long messages"
            )
        
        return suggestions

    async def _get_performance_data(self, content: str, platform: str) -> Dict:
        """Get historical performance data for similar content"""
        try:
            if platform == "twitter":
                # Get recent tweet performance
                stmt = select(Tweet).order_by(Tweet.created_at.desc()).limit(10)
                result = await self.db.execute(stmt)
                tweets = result.scalars().all()
                
                return {
                    "recent_performance": [
                        {
                            "content": tweet.content,
                            "engagement": tweet.metadata.get("engagement", 0),
                            "posted_at": tweet.created_at.isoformat()
                        }
                        for tweet in tweets
                    ]
                }
            else:
                # Return cached or default performance data
                return self.performance_cache.get(platform, {
                    "recent_performance": []
                })
                
        except Exception as e:
            logger.error(f"Error getting performance data: {e}")
            return {"recent_performance": []}

    async def track_performance(
        self,
        content_id: str,
        platform: str,
        metrics: Dict
    ) -> None:
        """Track content performance for future optimization"""
        try:
            # Store performance data
            self.performance_cache[platform] = self.performance_cache.get(platform, {})
            self.performance_cache[platform][content_id] = {
                "metrics": metrics,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Trim cache if needed
            if len(self.performance_cache[platform]) > 100:
                # Keep only most recent 100 entries
                sorted_items = sorted(
                    self.performance_cache[platform].items(),
                    key=lambda x: x[1]["timestamp"],
                    reverse=True
                )
                self.performance_cache[platform] = dict(sorted_items[:100])
                
        except Exception as e:
            logger.error(f"Error tracking performance: {e}")

    async def get_ab_test_variants(
        self,
        content: str,
        platform: str,
        num_variants: int = 2
    ) -> List[Dict]:
        """Generate A/B test variants for content"""
        variants = []
        try:
            base_optimization = await self.optimize_content(content, platform)
            variants.append({
                "variant": "A",
                "content": content,
                "metrics": base_optimization["metrics"]
            })
            
            # Generate additional variants
            for i in range(num_variants - 1):
                variant = await self.optimize_content(
                    base_optimization["optimized_content"],
                    platform,
                    {"variation_level": i + 1}
                )
                variants.append({
                    "variant": chr(66 + i),  # B, C, D, etc.
                    "content": variant["optimized_content"],
                    "metrics": variant["metrics"]
                })
            
            return variants
            
        except Exception as e:
            logger.error(f"Error generating A/B test variants: {e}")
            return [{"variant": "A", "content": content, "metrics": {}}]

    async def collaborative_iteration(
        self,
        content: str,
        feedback: str,
        platform: str
    ) -> Dict:
        """Handle collaborative content iteration with feedback"""
        try:
            # Create iteration prompt
            iteration_prompt = (
                f"Improve this {platform} content based on feedback:\n\n"
                f"Content: {content}\n\n"
                f"Feedback: {feedback}\n\n"
                "Provide specific improvements while maintaining the core message."
            )
            
            # Get improvement suggestions
            result = await self.rag.query(iteration_prompt)
            
            # Optimize the improved content
            optimized = await self.optimize_content(
                result["answer"],
                platform
            )
            
            return {
                "status": "success",
                "original": content,
                "improved": optimized["optimized_content"],
                "suggestions": optimized["suggestions"],
                "confidence": result["confidence"]
            }
            
        except Exception as e:
            logger.error(f"Error in collaborative iteration: {e}")
            return {
                "status": "error",
                "message": "Failed to process iteration",
                "error": str(e)
            }
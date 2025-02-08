import tweepy
from typing import Dict, List, Optional
import logging
from ..core.config import settings
from ..core.rag import EnhancedRAGSystem
from ..core.content_advisor import ContentAdvisor
from ..core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class TwitterManager:
    def __init__(self, rag_system: EnhancedRAGSystem):
        """Initialize Twitter Manager with API client and RAG system"""
        self.rag_system = rag_system
        self.draft_tweets: Dict[str, Dict] = {}  # Store drafts by user_id
        self.client = None
        self.followed_accounts = []
        self._setup_twitter_client()

    def _setup_twitter_client(self):
        """Initialize Twitter API client"""
        try:
            self.client = tweepy.Client(
                consumer_key=settings.TWITTER_API_KEY,
                consumer_secret=settings.TWITTER_API_SECRET,
                access_token=settings.TWITTER_ACCESS_TOKEN,
                access_token_secret=settings.TWITTER_ACCESS_SECRET
            )
            logger.info("Twitter client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Twitter client: {e}")
            self.client = None

    async def optimize_tweet(self, content: str) -> Dict:
        """Optimize a tweet using ContentAdvisor"""
        try:
            async with AsyncSessionLocal() as session:
                advisor = ContentAdvisor(self.rag_system, session)
                result = await advisor.optimize_content(content, "twitter")
                
                if result["status"] == "success":
                    suggestions = {
                        "improvements": result["suggestions"],
                        "hashtags": result["tags"]["hashtags"],
                        "engagement_score": result["metrics"]["engagement_score"],
                        "best_time": result["metrics"]["best_time"],
                        "recommended_hashtags": result["tags"]["hashtags"]
                    }
                    return {
                        "status": "success",
                        "content": result["optimized_content"],
                        "suggestions": suggestions
                    }
                return result
        except Exception as e:
            logger.error(f"Error optimizing tweet: {e}")
            return {
                "status": "error",
                "message": "Failed to optimize tweet"
            }

    async def create_draft(self, user_id: str, content: str) -> Dict:
        """Create a new tweet draft without initial optimization"""
        try:
            logger.info(f"Creating draft for user {user_id}")
            
            self.draft_tweets[user_id] = {
                'content': content,
                'original_content': content,
                'version': 1,
                'suggestions': {
                    'improvements': [],
                    'recommended_hashtags': ['#SuperteamVN', '#Web3Vietnam', '#BuildWeb3']
                },
                'metrics': {
                    'engagement_score': 0,
                    'best_time': 'N/A'
                }
            }

            # Basic validation
            if len(content) > 280:
                self.draft_tweets[user_id]['suggestions']['improvements'].append(
                    "⚠️ Tweet exceeds 280 character limit"
                )
            
            # Check mentions
            mentioned_users = [word[1:] for word in content.split() if word.startswith('@')]
            for username in mentioned_users:
                if not any(acc['username'].lower() == username.lower() for acc in self.followed_accounts):
                    self.draft_tweets[user_id]['suggestions']['improvements'].append(
                        f"@{username} is not in followed accounts"
                    )

            return {
                'status': 'success',
                'message': 'Draft created successfully',
                'content': content,
                'suggestions': self.draft_tweets[user_id]['suggestions']
            }

        except Exception as e:
            logger.error(f"Error creating draft: {e}")
            return {
                'status': 'error',
                'message': 'Failed to create draft'
            }

    async def preview_draft(self, user_id: str) -> Dict:
        """Get the current draft for a user"""
        try:
            logger.info(f"Getting preview for user {user_id}")
            
            if user_id not in self.draft_tweets:
                return {
                    'status': 'error',
                    'message': 'No draft found. Use /tweet command to create a draft first.'
                }

            draft = self.draft_tweets[user_id]
            
            response = {
                'status': 'success',
                'draft': {
                    'content': draft['content'],
                    'version': draft['version'],
                    'suggestions': draft['suggestions'],
                    'metrics': draft.get('metrics', {
                        'engagement_score': 0,
                        'best_time': 'N/A'
                    })
                }
            }
            
            logger.info(f"Retrieved draft version {draft['version']} for user {user_id}")
            return response

        except Exception as e:
            logger.error(f"Error getting draft preview: {e}")
            return {
                'status': 'error',
                'message': 'Failed to get draft preview'
            }

    async def improve_draft(self, user_id: str) -> Dict:
        """Get AI-powered improvements for current draft"""
        try:
            if user_id not in self.draft_tweets:
                return {
                    'status': 'error',
                    'message': 'No draft found'
                }

            draft = self.draft_tweets[user_id]
            content = draft['content']

            # Get new optimization suggestions
            optimization_result = await self.optimize_tweet(content)
            
            if optimization_result['status'] == 'success':
                new_suggestions = optimization_result['suggestions']
                
                # Merge new suggestions with existing ones
                draft['suggestions'].update(new_suggestions)
                draft['version'] += 1
                draft['metrics'] = {
                    'engagement_score': new_suggestions.get('engagement_score', 0),
                    'best_time': new_suggestions.get('best_time', 'N/A')
                }
                
                self.draft_tweets[user_id] = draft

                return {
                    'status': 'success',
                    'suggestions': new_suggestions
                }
            else:
                return optimization_result
                
        except Exception as e:
            logger.error(f"Error improving draft: {e}")
            return {
                'status': 'error',
                'message': 'Failed to improve draft'
            }

    async def update_draft(self, user_id: str, new_content: str) -> Dict:
        """Update existing draft content"""
        try:
            if user_id not in self.draft_tweets:
                return {
                    'status': 'error',
                    'message': 'No draft found'
                }

            # Create new draft with optimization
            result = await self.create_draft(user_id, new_content)
            
            if result['status'] == 'success':
                # Increment version from previous draft
                self.draft_tweets[user_id]['version'] = self.draft_tweets[user_id]['version'] + 1
                return result
            return {
                'status': 'error',
                'message': 'Failed to update draft'
            }
        except Exception as e:
            logger.error(f"Error updating draft: {e}")
            return {
                'status': 'error',
                'message': 'Failed to update draft'
            }

    async def generate_ab_variants(self, content: str) -> Dict:
        """Generate A/B test variants for a tweet"""
        try:
            async with AsyncSessionLocal() as session:
                advisor = ContentAdvisor(self.rag_system, session)
                variants = await advisor.get_ab_test_variants(content, "twitter", num_variants=3)
                
                return {
                    'status': 'success',
                    'variants': variants
                }
        except Exception as e:
            logger.error(f"Error generating A/B variants: {e}")
            return {
                'status': 'error',
                'message': 'Failed to generate variants'
            }

    async def publish_draft(self, user_id: str) -> Dict:
        """Publish the current draft tweet"""
        try:
            if user_id not in self.draft_tweets:
                return {
                    'status': 'error',
                    'message': 'No draft found'
                }

            draft = self.draft_tweets[user_id]
            content = draft['content']

            if self.client:
                try:
                    # Use v2 create_tweet method
                    tweet = self.client.create_tweet(text=content)
                    
                    # Clear the draft
                    del self.draft_tweets[user_id]
                    
                    return {
                        'status': 'success',
                        'message': 'Tweet published successfully',
                        'content': content,
                        'tweet_id': tweet.data['id'],
                        'metrics': draft['metrics']
                    }
                except tweepy.errors.TweepyException as e:
                    logger.error(f"Twitter API error: {e}")
                    return {
                        'status': 'error',
                        'message': f'Failed to publish tweet: {str(e)}'
                    }
            else:
                # Simulation mode if no Twitter client
                logger.warning("Publishing in simulation mode - no Twitter client")
                del self.draft_tweets[user_id]
                return {
                    'status': 'success',
                    'message': 'Tweet published (SIMULATION MODE)',
                    'content': content,
                    'metrics': draft['metrics']
                }
        except Exception as e:
            logger.error(f"Error publishing draft: {e}")
            return {
                'status': 'error',
                'message': 'Failed to publish tweet'
            }
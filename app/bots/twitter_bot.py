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
            auth = tweepy.OAuthHandler(
                settings.TWITTER_API_KEY,
                settings.TWITTER_API_SECRET
            )
            auth.set_access_token(
                settings.TWITTER_ACCESS_TOKEN,
                settings.TWITTER_ACCESS_SECRET
            )
            self.client = tweepy.API(auth)
            
            # Get followed accounts
            self._update_followed_accounts()
            logger.info("Twitter client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Twitter client: {e}")
            self.client = None

    def _update_followed_accounts(self):
        """Update the list of accounts followed by Superteam VN"""
        try:
            if not self.client:
                return
            
            # Get followers (limited to 200 for efficiency)
            following = self.client.get_friend_ids()
            user_objects = self.client.lookup_users(user_id=following[:100])
            
            self.followed_accounts = [
                {
                    'id': user.id,
                    'username': user.screen_name,
                    'name': user.name
                }
                for user in user_objects
            ]
            logger.info(f"Updated followed accounts: {len(self.followed_accounts)} accounts")
        except Exception as e:
            logger.error(f"Error updating followed accounts: {e}")

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
        """Create a new tweet draft with AI-powered suggestions"""
        try:
            # First optimize the content
            optimization_result = await self.optimize_tweet(content)
            if optimization_result['status'] != 'success':
                return optimization_result

            optimized_content = optimization_result['content']
            suggestions = optimization_result['suggestions']

            # Add length-based suggestions
            if len(optimized_content) > 240:
                suggestions['improvements'].append("⚠️ Tweet is too long, consider shortening")
            elif len(optimized_content) < 50:
                suggestions['improvements'].append("Consider adding more context for better engagement")

            # Check mentions against followed accounts
            mentioned_users = [word[1:] for word in optimized_content.split() if word.startswith('@')]
            if mentioned_users:
                for username in mentioned_users:
                    if not any(acc['username'].lower() == username.lower() for acc in self.followed_accounts):
                        suggestions['improvements'].append(f"@{username} is not in followed accounts")

            # Store draft with metadata
            self.draft_tweets[user_id] = {
                'content': optimized_content,
                'original_content': content,
                'suggestions': suggestions,
                'version': 1,
                'metrics': {
                    'engagement_score': suggestions.get('engagement_score', 0),
                    'best_time': suggestions.get('best_time', 'N/A')
                }
            }

            return {
                'status': 'success',
                'message': 'Draft created successfully',
                'content': optimized_content,
                'suggestions': suggestions
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
            if user_id not in self.draft_tweets:
                return {
                    'status': 'error',
                    'message': 'No draft found'
                }

            draft = self.draft_tweets[user_id]
            return {
                'status': 'success',
                'draft': draft
            }
        except Exception as e:
            logger.error(f"Error getting draft: {e}")
            return {
                'status': 'error',
                'message': 'Failed to get draft'
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
                    # Final optimization check before posting
                    final_check = await self.optimize_tweet(content)
                    if final_check['status'] == 'success' and final_check['metrics']['engagement_score'] > draft['metrics']['engagement_score']:
                        content = final_check['content']

                    # Post tweet
                    tweet = self.client.update_status(content)
                    
                    # Track performance metrics
                    async with AsyncSessionLocal() as session:
                        advisor = ContentAdvisor(self.rag_system, session)
                        await advisor.track_performance('tweet', tweet.id, draft['metrics'])
                    
                    # Clear the draft
                    del self.draft_tweets[user_id]
                    
                    return {
                        'status': 'success',
                        'message': 'Tweet published successfully',
                        'content': content,
                        'tweet_id': tweet.id,
                        'metrics': draft['metrics']
                    }
                except tweepy.TweepError as e:
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
from langchain_community.llms import LlamaCpp
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
from .config import settings
import logging

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a helpful assistant for Superteam Vietnam. Use the following information to answer questions.
If you're not confident about the answer or don't have enough context, say "I don't have enough information to answer this question accurately."

Context:
{context}

Question: {question}

Instructions:
1. If the context is relevant, provide a clear and concise answer.
2. If you're not confident, say so clearly.
3. Only use information from the provided context.

Answer: Let me help you with that."""

class EnhancedRAGSystem:
    def __init__(self):
        """Initialize the enhanced RAG system with vector storage and improved chunking"""
        try:
            logger.info("Initializing Enhanced RAG System...")
            self._setup_embeddings()
            self._setup_vector_store()
            self._setup_text_splitter()
            self._setup_llm()
            self._setup_prompt()
            
            # Load initial knowledge base
            self._load_knowledge_base()
            
            logger.info("Enhanced RAG System initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Enhanced RAG System: {e}")
            raise

    def _setup_embeddings(self):
        """Initialize the embedding model"""
        try:
            logger.info("Setting up embeddings...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'}
            )
        except Exception as e:
            logger.error(f"Error setting up embeddings: {e}")
            raise

    def _setup_vector_store(self):
        """Initialize the vector store"""
        try:
            logger.info("Setting up vector store...")
            vector_store_path = Path(settings.VECTOR_STORE_PATH)
            vector_store_path.mkdir(parents=True, exist_ok=True)
            
            self.vector_store = Chroma(
                persist_directory=str(vector_store_path),
                embedding_function=self.embeddings
            )
        except Exception as e:
            logger.error(f"Error setting up vector store: {e}")
            raise

    def _setup_text_splitter(self):
        """Initialize the text splitter for document chunking"""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def _setup_llm(self):
        """Initialize the LLM with optimized settings"""
        try:
            logger.info("Setting up LLM...")
            model_path = Path(settings.MODEL_PATH)
            
            if not model_path.exists():
                logger.error(f"Model file not found at: {model_path.absolute()}")
                raise FileNotFoundError(f"Model not found at {model_path}")
            
            callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
            
            self.llm = LlamaCpp(
                model_path=str(model_path),
                temperature=0.1,
                max_tokens=settings.MAX_TOKENS,
                n_ctx=settings.CONTEXT_LENGTH,
                n_threads=settings.THREADS,
                callback_manager=callback_manager,
                n_gpu_layers=settings.GPU_LAYERS,
                use_mlock=True,
                use_mmap=True,
                top_p=0.1,
                repeat_penalty=1.2
            )
        except Exception as e:
            logger.error(f"Error setting up LLM: {e}")
            raise

    def _setup_prompt(self):
        """Initialize the prompt template and chain"""
        self.prompt = PromptTemplate(
            template=PROMPT_TEMPLATE,
            input_variables=["context", "question"]
        )
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            verbose=True
        )

    def _load_knowledge_base(self):
        """Load initial knowledge base content"""
        try:
            kb_path = Path("data/knowledge_base/about.txt")
            logger.info(f"Loading knowledge base from: {kb_path}")
            
            if not kb_path.exists():
                logger.warning("Knowledge base file not found")
                return
            
            with open(kb_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                logger.warning("Knowledge base file is empty")
                return
                
            # Add to vector store
            chunks = self.text_splitter.split_text(content)
            logger.info(f"Split knowledge base into {len(chunks)} chunks")
            
            # Add chunks to vector store with metadata
            self.vector_store.add_texts(
                texts=chunks,
                metadatas=[{
                    "source": "knowledge_base",
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                } for i in range(len(chunks))]
            )
            
            logger.info("Successfully loaded knowledge base into vector store")
            
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
            raise

    async def add_document(self, content: str, metadata: Optional[Dict] = None) -> bool:
        """Add a document to the vector store with proper chunking"""
        try:
            logger.info("Adding new document to vector store...")
            
            # Split the document into chunks
            chunks = self.text_splitter.split_text(content)
            
            # Add metadata to each chunk if provided
            if metadata:
                chunk_metadata = [metadata.copy() for _ in chunks]
            else:
                chunk_metadata = [{}] * len(chunks)
            
            # Add chunk index to metadata
            for i, meta in enumerate(chunk_metadata):
                meta['chunk_index'] = i
                meta['total_chunks'] = len(chunks)
            
            # Add chunks to vector store
            self.vector_store.add_texts(
                texts=chunks,
                metadatas=chunk_metadata
            )
            
            logger.info(f"Successfully added {len(chunks)} chunks to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return False

    def _calculate_confidence(self, similarities: List[float]) -> float:
        """Calculate confidence score based on similarity scores"""
        if not similarities:
            return 0.0
        
        # Weight recent similarities more heavily
        weights = np.exp(np.linspace(-1, 0, len(similarities)))
        weighted_similarities = np.array(similarities) * weights
        
        # Calculate confidence score
        confidence = float(np.mean(weighted_similarities))
        
        return confidence

    async def query(self, question: str, confidence_threshold: float = 0.6) -> Dict:
        """
        Query the RAG system with confidence scoring
        Returns a dictionary with answer and confidence score
        """
        try:
            logger.info(f"Processing query: {question}")
            
            # Get relevant documents and their similarity scores
            docs_and_scores = self.vector_store.similarity_search_with_score(
                question,
                k=3  # Get top 3 most relevant chunks
            )
            
            if not docs_and_scores:
                return {
                    "answer": "I don't have enough information to answer this question accurately.",
                    "confidence": 0.0
                }
            
            # Extract documents and scores
            docs = [doc for doc, _ in docs_and_scores]
            scores = [score for _, score in docs_and_scores]
            
            # Calculate confidence
            confidence = self._calculate_confidence(scores)
            
            if confidence < confidence_threshold:
                return {
                    "answer": "While I have some information, I'm not confident enough to provide an accurate answer to this question.",
                    "confidence": confidence
                }
            
            # Combine relevant contexts
            context = "\n\n".join(doc.page_content for doc in docs)
            
            # Generate answer using LLM
            response = self.chain.run(
                context=context,
                question=question
            )
            
            return {
                "answer": response.strip(),
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "answer": "Sorry, I encountered an error while processing your question. Please try again later.",
                "confidence": 0.0
            }

    async def debug_knowledge_base(self) -> bool:
        """Debug method to check vector store content"""
        try:
            # Try a simple query to get all documents
            docs = self.vector_store.similarity_search(
                "Superteam Vietnam",
                k=10
            )
            
            logger.info(f"Found {len(docs)} documents in vector store")
            for i, doc in enumerate(docs):
                logger.info(f"Document {i + 1}:")
                logger.info(f"Content: {doc.page_content[:100]}...")
                logger.info(f"Metadata: {doc.metadata}")
            
            return len(docs) > 0
            
        except Exception as e:
            logger.error(f"Error checking vector store: {e}")
            return False
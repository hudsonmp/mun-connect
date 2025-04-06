"""
Summarization module for background guide processing.

This module provides functions to summarize document sections using either
local models or OpenAI API.
"""

import os
import openai
from typing import Optional, Dict, Any
from transformers import pipeline

# Set OpenAI API key from environment if available
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

def summarize_content(
    text: str, 
    use_openai: bool = True,
    summarizer: Optional[pipeline] = None,
    max_length: int = 200,
    min_length: int = 50,
    openai_model: str = "gpt-4o-mini"
) -> str:
    """
    Summarize text content using either a local model or OpenAI API.
    
    Args:
        text: Text to summarize
        use_openai: Whether to use OpenAI API
        summarizer: Pre-loaded summarization pipeline
        max_length: Maximum length of summary
        min_length: Minimum length of summary
        openai_model: OpenAI model to use
        
    Returns:
        Generated summary
    """
    # If text is very short, return it as is
    if len(text.split()) < min_length:
        return text
    
    if use_openai and OPENAI_API_KEY:
        return summarize_with_openai(text, openai_model)
    elif summarizer:
        return summarize_with_local_model(text, summarizer, max_length, min_length)
    else:
        # Fallback to a simple extractive summary
        return extractive_summary(text, max_length)

def summarize_with_openai(text: str, model: str = "gpt-4o-mini") -> str:
    """
    Generate a summary using OpenAI API.
    
    Args:
        text: Text to summarize
        model: OpenAI model to use
        
    Returns:
        Generated summary
    """
    try:
        # Handle text length - OpenAI models have token limits
        # A simple approximation is to count words and limit to 4000 words (~3000 tokens)
        words = text.split()
        if len(words) > 4000:
            # Take first and last portions of the text
            text = " ".join(words[:2000]) + " ... " + " ".join(words[-2000:])
        
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert at summarizing complex documents. Create a concise but comprehensive summary that captures the key points, main themes, and essential information from the text provided."},
                {"role": "user", "content": f"Please summarize the following text, focusing on the key points and main themes:\n\n{text}"}
            ],
            temperature=0.5,
            max_tokens=500,
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error using OpenAI API for summarization: {e}")
        # Fallback to simple extractive summary
        return extractive_summary(text)

def summarize_with_local_model(
    text: str, 
    summarizer: pipeline, 
    max_length: int = 200, 
    min_length: int = 50
) -> str:
    """
    Generate a summary using a local model via Hugging Face pipeline.
    
    Args:
        text: Text to summarize
        summarizer: Pre-loaded summarization pipeline
        max_length: Maximum length of summary
        min_length: Minimum length of summary
        
    Returns:
        Generated summary
    """
    try:
        # Handle long texts by breaking into chunks (limit texts to ~1000 tokens per chunk)
        chunks = []
        sentences = text.split(". ")
        current_chunk = ""
        
        for sentence in sentences:
            # Add sentence and period back
            new_sentence = sentence + ". "
            
            # If adding this sentence would make the chunk too long, add chunk to list and start new chunk
            if len(current_chunk.split() + new_sentence.split()) > 500:
                chunks.append(current_chunk)
                current_chunk = new_sentence
            else:
                current_chunk += new_sentence
        
        # Add the last chunk if not empty
        if current_chunk:
            chunks.append(current_chunk)
        
        # Summarize each chunk
        chunk_summaries = []
        for chunk in chunks:
            if not chunk.strip():
                continue
                
            result = summarizer(
                chunk, 
                max_length=max(min_length, max_length // len(chunks)), 
                min_length=min(min_length, len(chunk.split()) // 4),
                do_sample=False
            )
            chunk_summaries.append(result[0]['summary_text'])
        
        # Join chunk summaries
        if chunk_summaries:
            return " ".join(chunk_summaries)
        else:
            return extractive_summary(text, max_length)
            
    except Exception as e:
        print(f"Error using local model for summarization: {e}")
        # Fallback to simple extractive summary
        return extractive_summary(text, max_length)

def extractive_summary(text: str, max_length: int = 200) -> str:
    """
    Create a simple extractive summary by selecting key sentences.
    
    Args:
        text: Text to summarize
        max_length: Maximum length of summary in words
        
    Returns:
        Extractive summary
    """
    # Split text into sentences
    sentences = text.split(". ")
    
    # If very few sentences, return the text as is (truncated if needed)
    if len(sentences) <= 3:
        words = text.split()
        if len(words) > max_length:
            return " ".join(words[:max_length])
        return text
    
    # Select key sentences (first sentence, last sentence, and a middle sentence)
    key_sentences = [
        sentences[0],
        sentences[len(sentences) // 2],
        sentences[-1]
    ]
    
    # Add more sentences if we have room (every Nth sentence)
    if len(sentences) > 5 and max_length > 100:
        step = len(sentences) // 3
        for i in range(step, len(sentences) - step, step):
            key_sentences.append(sentences[i])
            
            # Check if we've reached the max length
            summary = ". ".join(key_sentences) + "."
            if len(summary.split()) >= max_length:
                break
    
    # Format and return the summary
    summary = ". ".join(key_sentences)
    if not summary.endswith("."):
        summary += "."
    
    return summary

def extract_key_insights(text: str, summary: str, use_openai: bool = True) -> list:
    """
    Extract key insights and bullet points from text and summary.
    
    Args:
        text: Original text
        summary: Generated summary
        use_openai: Whether to use OpenAI API
        
    Returns:
        List of key insights as bullet points
    """
    if use_openai and OPENAI_API_KEY:
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting key insights from complex documents. Create a list of 3-5 concise bullet points capturing the most important information."},
                    {"role": "user", "content": f"Extract 3-5 key insights as bullet points from this text and its summary.\n\nTEXT: {text}\n\nSUMMARY: {summary}"}
                ],
                temperature=0.3,
                max_tokens=300,
            )
            
            # Process the response to extract bullet points
            result = response.choices[0].message.content
            bullet_points = [point.strip().lstrip('•-*').strip() for point in result.split('\n') if point.strip()]
            return bullet_points
            
        except Exception as e:
            print(f"Error using OpenAI API for key insights: {e}")
            # Fallback to rule-based extraction
    
    # Simple rule-based extraction of potential key points
    insights = []
    
    # Look for sentences that might contain key information
    sentences = text.split(". ")
    for sentence in sentences:
        # Look for sentences that likely contain key points
        lower_sent = sentence.lower()
        if any(kw in lower_sent for kw in ["important", "key", "critical", "significant", "notable", "essential"]):
            insights.append(sentence)
        
        # Look for sentences with numbers or statistics
        if any(char.isdigit() for char in sentence):
            insights.append(sentence)
    
    # If we found a lot, prioritize and limit
    if len(insights) > 5:
        insights = insights[:5]
    
    # If we found very few, add some from the summary
    if len(insights) < 3:
        summary_sentences = summary.split(". ")
        for sentence in summary_sentences:
            if sentence not in insights and len(insights) < 3:
                insights.append(sentence)
    
    return insights 
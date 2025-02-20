from typing import AsyncIterator
from ollama import chat
from pydantic import BaseModel
from groq import AsyncGroq, Groq

class Queries(BaseModel):
    queries: list[str]
    
class Evaluation(BaseModel):
    is_relevant: bool


def invoke_ollama(
    model,
    system_prompt,
    user_prompt,
    output_format=None,
):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = chat(
        model=model,
        messages=messages,
        format="output_format.model_json_schema() if output_format else None",
    )

    if output_format:
        return output_format.model_validate_json(response.message.content)
    else:
        return response.message.content


def invoke_groq(
    system_prompt,
    user_prompt,
    output_format=None,
    model="llama-3.3-70b-versatile",
):
    client = Groq()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    # Configure the API call based on whether we want JSON output or not
    if output_format:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
    else:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
        )
    
    # Parse the response based on the output format
    if output_format:
        return output_format.model_validate_json(response.choices[0].message.content)
    else:
        return response.choices[0].message.content
    

def format_docs_with_metadata(documents):
    formatted_docs = []
    for doc in documents:
        source = doc.metadata.get("source", 'Unknown source')
        formated_doc = f"Source: {source}\n Content: {doc.page_content}"
        
        formatted_docs.append(formated_doc)
    
    return "\n\n--\n\n".join(formatted_docs)


async def invoke_groq_stream(
    system_prompt: str,
    user_prompt: str,
    model: str = "llama-3.3-70b-versatile",
) -> AsyncIterator[str]:
    """Streaming version of invoke_groq"""
    client = AsyncGroq()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        stream=True
    )
    
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
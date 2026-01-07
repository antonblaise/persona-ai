import os
import subprocess
import sys
import asyncio
from ollama import AsyncClient

def get_git_diff():
    """
    Retrieves the diff of all changes (staged and unstaged) relative to HEAD.
    """
    try:
        # Get the diff of changes (Staged + Unstaged)
        # using 'HEAD' ensures we see everything changed since the last commit
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace' # Handle potential encoding issues in source files
        )
        
        if result.returncode != 0:
            print(f"Error running git command: {result.stderr}")
            sys.exit(1)
            
        return result.stdout.strip()

    except FileNotFoundError:
        print("Error: Git is not installed or not found in PATH.")
        sys.exit(1)

def get_untracked_files():
    """
    Retrieves a list of untracked files to add context.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.stdout.strip()
    except Exception:
        return ""

def create_llm_prompt(diff_output, untracked_files):
    """
    Composes the prompt for the LLM.
    """
    if not diff_output and not untracked_files:
        return None

    # Truncate very large diffs to avoid hitting token limits (approximate check)
    # 1 char ~= 1 byte. 1 token ~= 4 chars. 
    # If diff > 100k chars, it might be too big for some web interfaces.
    if len(diff_output) > 50000: 
        diff_output = diff_output[:50000] + "\n...[Diff truncated due to length]..."

    prompt = (
        "Act as a senior software developer. Write a detailed, standardized git commit message "
        "based on the code changes provided below.\n\n"
        "**Requirements:**\n"
        "1. Use the format: `<type>: <subject>` (e.g., `feat: add user login`, `fix: resolve null pointer`).\n"
        "2. Keep the subject line under 100 characters if possible.\n"
        "3. Provide a bulleted body description if the changes are complex.\n"
        "4. Do not include unrelated chatter, just the commit message.\n\n"
        "**Changes Context:**\n"
    )

    if untracked_files:
        prompt += f"New Untracked Files:\n{untracked_files}\n\n"

    prompt += f"**Git Diff:**\n```diff\n{diff_output}\n```"
    
    return prompt

async def talk_to_llm(prompt: str) -> str:

    async_client = AsyncClient()
    response = await async_client.chat(
        model="deepseek-v3.1:671b-cloud",
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        think=False
    )
    return response['message']['content']

def main():
    print("--- Analyzing Repository Changes ---")
    
    diff = get_git_diff()
    untracked = get_untracked_files()

    if not diff and not untracked:
        print("No local changes found (Clean working tree).")
        return

    prompt = create_llm_prompt(diff, untracked)
    
    print("\n--- Commit message ---\n")
    print(asyncio.run(talk_to_llm(prompt=prompt)))
    print("\n----------------------------")


if __name__ == "__main__":
    main()
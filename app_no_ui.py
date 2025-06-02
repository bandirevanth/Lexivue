import asyncio
import os
import shutil
import subprocess
import tempfile
from typing import List
import logging

from moviepy import concatenate_videoclips, VideoFileClip
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from config import api_key
import nest_asyncio
nest_asyncio.apply()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure your Gemini API key
gemini_llm = GeminiModel(
    'gemini-2.0-flash', provider=GoogleGLAProvider(api_key=api_key)
)


class ChapterDescription(BaseModel):
    """Describes a chapter in the video."""
    title: str = Field(description="Title of the chapter.")
    explanation: str = Field(description="Detailed explanation of the chapter's content, including how Manim should visualize it. Be very specific with Manim instructions, including animations, shapes, positions, colors, and timing. Include LaTeX for mathematical formulas. Specify scene transitions. Example: 'Create a number line. Animate a point moving along the number line to illustrate addition. Use Transform to show the equation changing. Transition to a new Scene.'")

class VideoOutline(BaseModel):
    """Describes the outline of the video."""
    title: str = Field(description="Title of the entire video.")
    chapters: List[ChapterDescription] = Field(description="List of chapters in the video.")

class ManimCode(BaseModel):
    """Describes the Manim code for a chapter."""
    code: str = Field(description="Complete Manim code for the chapter. Include all necessary imports. The code should create a single scene. Add comments to explain the code. Do not include any comments that are not valid Python comments. Ensure the code is runnable.")

outline_agent = Agent(
    model=gemini_llm,
    result_type=VideoOutline,
    system_prompt="""
    You are a video script writer. Your job is to create a clear and concise outline for an educational video explaining a concept.
    The video should have a title and a list of chapters (maximum 3). Each chapter should have a title and a detailed explanation.
    The explanation should be very specific about how the concept should be visualized using Manim. Include detailed instructions
    for animations, shapes, positions, colors, and timing. Use LaTeX for mathematical formulas. Specify scene transitions.
    Do not include code, only explanations.
    """
)

manim_agent = Agent(
    model=gemini_llm,
    result_type=ManimCode,
    system_prompt="""
    You are a Manim code generator. Your job is to create Manim code for a single chapter of a video, given a detailed explanation of the chapter's content and how it should be visualized.
    The code should be complete and runnable. Include all necessary imports. The code should create a single scene. Add comments to explain the code.
    Do not include any comments that are not valid Python comments. Ensure the code is runnable. Do not include any text outside of the code block.

    """
)

code_fixer_agent = Agent(
    model=gemini_llm,
    result_type=ManimCode,
    system_prompt="""
    You are a Manim code debugging expert. You will receive Manim code that failed to execute and the error message.
    Your task is to analyze the code and the error, identify the issue, and provide corrected, runnable Manim code.
    Ensure the corrected code addresses the error and still aims to achieve the visualization described in the original code.
    Include all necessary imports and ensure the code creates a single scene. Add comments to explain the changes you made.
    Do not include any comments that are not valid Python comments. Ensure the code is runnable. Do not include any text outside of the code block.
    """
)

def generate_manim_code(chapter_description: ChapterDescription) -> str:
    """Generates initial Manim code for a single chapter."""
    logging.info(f"Generating Manim code for chapter: {chapter_description.title}")
    result = manim_agent.run_sync(f"title: {chapter_description.title}. Explanation: {chapter_description.explanation}")
    return result.data.code

def fix_manim_code(error: str, current_code: str) -> str:
    """Attempts to fix the Manim code that resulted in an error."""
    logging.info(f"Attempting to fix Manim code due to error: {error}")
    result = code_fixer_agent.run_sync(f"Error: {error}\nCurrent Code: {current_code}")
    return result.data.code

def generate_video_outline(concept: str) -> VideoOutline:
    """Generates the video outline."""
    logging.info(f"Generating video outline for concept: {concept}")
    result = outline_agent.run_sync(concept)
    return result.data

def create_video_from_code(code: str, chapter_number: int) -> str:
    """Creates a video from Manim code and returns the video file path using subprocess.Popen."""
    with open("temp.py", "w") as temp_file:
        temp_file.write(code)
        temp_file_name = temp_file.name

    process = None
    try:
        command = ["manim", temp_file_name, "-ql", "--disable_caching"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
        stdout, stderr = process.communicate(timeout=60)  # Add a timeout to prevent indefinite blocking

        if process.returncode == 0:
            logging.info(f"Manim execution successful for chapter {chapter_number}.")
            logging.debug(f"Manim stdout:\n{stdout}")
            logging.debug(f"Manim stderr:\n{stderr}")
        else:
            error_msg = f"Manim execution failed for chapter {chapter_number} with return code {process.returncode}:\nStdout:\n{stdout}\nStderr:\n{stderr}"
            logging.error(str(error_msg).split('\n')[-1])
            raise subprocess.CalledProcessError(process.returncode, command, output=stdout.encode(), stderr=stderr.encode())

    except subprocess.TimeoutExpired:
        logging.error(f"Manim process timed out for chapter {chapter_number}.")
        if process:
            process.kill()
        raise
    except FileNotFoundError:
        logging.error("Error: The 'manim' command was not found. Ensure Manim is installed and in your system's PATH.")
        raise
    finally:
        pass
        # if os.path.exists(temp_file_name):
        #     os.remove(temp_file_name)

    # Construct the video file name. Manim names the file based on the class name.
    # Extract the class name from the python code.
    import re
    match = re.search(r"class\s+(\w+)\(Scene\):", code)
    if match:
        class_name = match.group(1)
        video_file_name = f"{class_name}.mp4"
        return video_file_name
    else:
        raise ValueError(f"Could not extract class name from Manim code for chapter {chapter_number}")

async def main(concept: str):
    """Generates a video explanation for a given concept using Manim with error correction."""
    logging.info(f"Generating video for concept: {concept}")
    outline = generate_video_outline(concept)
    logging.info(f"Video outline: {outline}")

    video_files = []
    for i, chapter in enumerate(outline.chapters):
        logging.info(f"Processing chapter {i + 1}: {chapter.title}")
        manim_code = generate_manim_code(chapter)
        logging.debug(f"Generated Manim code for chapter {i + 1}:\n{manim_code}")

        success = False
        attempts = 0
        max_attempts = 2  # Try fixing the code once

        while attempts < max_attempts and not success:
            try:
                video_file = create_video_from_code(manim_code, i + 1)
                video_files.append(video_file)
                logging.info(f"Video file created for chapter {i + 1}: {video_file}")
                success = True
            except subprocess.CalledProcessError as e:
                attempts += 1
                logging.error(f"Manim execution failed for chapter {i + 1} (Attempt {attempts}): {e}")
                logging.info(f"Attempting to fix the code...")
                manim_code = fix_manim_code(str(e), manim_code)
                logging.debug(f"Fixed Manim code (Attempt {attempts}):\n{manim_code}")
            except ValueError as e:
                logging.error(f"Error processing Manim code for chapter {i + 1}: {e}")
                return  # Stop processing if a critical error occurs with code structure
            except FileNotFoundError:
                logging.error("Manim not found. Please ensure it's installed and in your PATH.")
                return
            except subprocess.TimeoutExpired:
                logging.error(f"Manim process timed out for chapter {i + 1}. Attempting to fix...")
                manim_code = fix_manim_code(f"Manim process timed out.", manim_code)
                logging.debug(f"Fixed Manim code (Attempt {attempts}):\n{manim_code}")

        if not success:
            logging.error(f"Failed to generate video for chapter {i + 1} after {max_attempts} attempts. Skipping chapter.")
            continue

    # Combine the video files
    if video_files:
        logging.info("Combining video files...")
        clips = [VideoFileClip("./media/videos/temp/480p15/"+video_file) for video_file in video_files]
        final_video_path = f"final.mp4"
        final_clip = concatenate_videoclips(clips)
        final_clip.write_videofile(final_video_path, codec="libx264", audio_codec="aac")
        final_clip.close()

        logging.info(f"Final video created: {final_video_path}")

        # Clean up intermediate video files
        for video_file in video_files:
            try:
                os.remove(video_file)
                logging.info(f"Deleted intermediate video file: {video_file}")
            except Exception as e:
                logging.error(f"Error deleting intermediate video file {video_file}: {e}")
    else:
        logging.warning("No video files to combine.")

if __name__ == "__main__":
    concept = input("Enter your Prompt: ")  # Replace with your concept
    asyncio.run(main(concept))
# Lexivue: An AI-powered Video Generator

## Overview

This project is a tool that automatically generates (explanatory) videos from a given prompt. 

It uses the following technologies:
**Pydantic AI** | **Google Gemini** | **Manim** | **MoviePy** 

In essence, you provide a prompt, and the system uses AI to create a video explaining the topic.

## Features

* Automatic video generation from a text prompt.
* Uses Gemini for prompt understanding and content creation.
* Leverages Manim for high-quality animations.
* Combines animations into a complete video using MoviePy.

## Setup Instructions

Here's how to get the video generator up and running:

1.  **Clone the Repository:**
    ```bash
    git clone <your_repository_url>
    cd <your_repository_directory>
    ```
    (Replace `<your_repository_url>` and `<your_repository_directory>` with the actual URL and directory.)

2.  **Configure the API Key:**

    * Create a copy of the `config-example.py` file and rename it to `config.py`.
    * Open `config.py` and add your Gemini API key:

        ```python
        api_key='<google-gemini-api-key>'"  # Replace with your actual Gemini API key
        ```

3.  **Install Dependencies:**

    * It's highly recommended to use a virtual environment to manage dependencies. For example:
        ```bash
        python3 -m venv .venv #create a virtual environment
        source .venv/bin/activate #activate the virtual environment.  If on windows use .\.venv\Scripts\activate
        ```
    * Install the required Python packages:
        ```bash
        pip install -r requirements.txt
        ```

4.  **Run the Application:**
    ```bash
    streamlit run app.py
    or
    python app_no_ui.py
    ```

## Usage

1.  Run the `app.py`/`app_no_ui.py` script as described in the setup instructions.
2.  The application will take a text prompt as input. (in streamlit/cmd line)
3.  The AI will process the prompt, generate a video script, and then create the video.
4.  The generated video will be saved to a `final.mp4` file.
5.  Don't forget to star me on GitHub and follow me! Thanks :)

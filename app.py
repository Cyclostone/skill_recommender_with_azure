from flask import Flask, request, jsonify
import pdfplumber
import openai
import requests
from flask import render_template, redirect, url_for
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

openai.api_key = "375f3ceb969a451ab35668c1a7e21812"
openai.azure_endpoint = "https://ai-endpoint-mk1.openai.azure.com/"
openai.api_type = "azure"
openai.api_version = "2024-06-01"

YOUTUBE_API_KEY = "AIzaSyD-jamz4GmuKFd9yNoI-bvFjL4rQ2LHtU4"
YOUTUBE_API_URL = 'https://www.googleapis.com/youtube/v3/search'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    #file = request.files['file']
    #job_title = request.form['job_title']

    file = request.files.get('file')
    job_title = request.form.get('job_title')


    if not file or not file.filename.endswith('.pdf'):
        return jsonify({"error": "Invalid file format. Please upload a PDF."}), 400
    else:
        text = extract_text_from_pdf(file)

        skill_comparison_result, course_recommendations = extract_and_compare_skills(text, job_title)

        return render_template('index.html', skill_comparison_result=skill_comparison_result, course_recommendations=course_recommendations)
        
    
def extract_text_from_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        return ' '.join(page.extract_text() for page in pdf.pages)


def extract_and_compare_skills(resume_text, job_title):
    prompt = (
    f"""You are analyzing a resume for the job title: {job_title}.
    First, read the provided resume carefully.
    Then, based on the skills in the resume, identify the **missing skills** required to be successful in the role of {job_title}.

    Important: I do not need the answer in code format, only provide the output as structured text, NOT in code.

    Format the response as plain text in the following structure:

    Missing Skills:
    - Skill 1
    - Skill 2
    - Skill 3
    ...

    Below is the user's resume:
    {resume_text}
    """
)

    response = openai.completions.create(
        model = 'gpt-35-turbo-instruct',
        prompt = prompt,
        max_tokens=100
    )

    result = response.choices[0].text.strip()
    missing_skills = extract_missing_skills_from_result(result)
    course_recommendations = get_courses_for_missing_skills(missing_skills)

    format_recommendation = format_recommendations(course_recommendations)
    print(result)
    print(course_recommendations)
    return result, format_recommendation

def extract_missing_skills_from_result(result): 
    missing_skills = []
    lines = result.splitlines()

    for line in lines:
        if line.startswith("-"):
            missing_skills.append(line[2:].strip())
    return missing_skills

def get_youtube_playlists(skill):
    params = {
        'part': 'snippet',
        'q': f'{skill} tutorial',
        'type': 'playlist',
        'maxResults': 5,
        'key': YOUTUBE_API_KEY
    }
    
    response = requests.get(YOUTUBE_API_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        return [{"platform": "Youtube", "title": item["snippet"]["title"], 
                "url": f'https://www.youtube.com/playlist?list={item["id"]["playlistId"]}'} 
                for item in data["items"]]
    
    return []

def get_courses_for_missing_skills(missing_skills):
    all_resources = []

    for skill in missing_skills:
        youtube_playlists = get_youtube_playlists(skill)

        all_resources.append({
            "skill_name": skill,
            "resources": youtube_playlists
        })

        return all_resources
    
def format_recommendations(course_recommendations):
    formatted_recommendations = ""

    for recommendation in course_recommendations:
        formatted_recommendations += f"<h3>{recommendation['skill_name']}</h3>\n<ul>"
        for resource in recommendation['resources']:
            formatted_recommendations += f"<li><a href='{resource['url']}' target='_blank'>{resource['title']}</a> ({resource['platform']})</li>\n"
        formatted_recommendations += "</ul>"

    return formatted_recommendations



if __name__ == '__main__':
    app.run(host = '0.0.0.0', port=8000)
from flask import Flask, render_template, request
from bs4 import BeautifulSoup
import requests
import re
import os
import openai

# Initialize OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

app = Flask(__name__)

def clean_text(text):
    """Remove unnecessary characters like HTML tags, URLs, and extra spaces."""
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    text = re.sub(r'<[^>]*>', '', text)  # Remove HTML tags
    text = re.sub(r'http[s]?://\S+', '', text)  # Remove URLs
    return text.strip()

def analyze_text(text):
    """Classifies the appropriateness of a text for an audience under 15 years old."""
    try:
        # instructions
        instruction = (
            "Classify whether the provided text is appropriate for an audience under 15 years old. "
            "Format the output as follows:\n\n"
            "Appropriateness: [Calculated Percentage]\n"
            "Suggestion: [Strongly Inappropriate for audiences under 15\n"
            "- Appropriate under supervision\n"
            "- Fully Appropriate]\n"
            "Analysis: [Provide a concise evaluation explaining the reasons for the score in one paragraph]"
        )
        
        # combination 
        prompt = f"#INSTRUCTION\n{instruction}\n\n#TEXT\n{text}"
        
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        result = response['choices'][0]['message']['content'].strip()
        
        # Extract information using regex
        appropriateness = re.search(r'Appropriateness: (\d+)', result)
        suggestion = re.search(r'Suggestion: (.*)', result)
        analysis = re.search(r'Analysis: (.*)', result)

        return {
            "appropriateness": appropriateness.group(1) if appropriateness else "N/A",
            "suggestion": suggestion.group(1) if suggestion else "N/A",
            "analysis": analysis.group(1) if analysis else "N/A"
        }

    except Exception as e:
        return {"error": f"Error in analysis: {str(e)}"}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form.get('url')
    if not url:
        return render_template('index.html', error_message="Please provide a valid URL.")

    try:
        # Fetch and parse the content from the URL
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Clean the title and paragraphs
        title = clean_text(soup.title.string) if soup.title else "No Title Found"
        paragraphs = [clean_text(p.text) for p in soup.find_all('p')]

        # Combine title and paragraphs for analysis
        text_for_analysis = title + " " + " ".join(paragraphs)

        # Perform the semantic analysis
        analysis_result = analyze_text(text_for_analysis)

        # Check if error exists in the result
        if "error" in analysis_result:
            print(f"Analysis Error: {analysis_result['error']}")
            return render_template('index.html', error_message=f"Error: {analysis_result['error']}")

        return render_template('results.html', 
                               title=title, 
                               paragraphs=paragraphs, 
                               appropriateness=analysis_result.get('appropriateness', "N/A"),
                               suggestion=analysis_result.get('suggestion', "N/A"),
                               analysis=analysis_result.get('analysis', "N/A"))

    except Exception as e:
        return render_template('index.html', error_message=f"Error: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)

import markdown
from flask import render_template, request, redirect, jsonify
import asyncio
from render_service import render_page_and_extract_text

def init_routes(app):

    @app.route('/', methods=['GET', 'POST'])
    def home():
        if request.method == 'POST':
            user_url = request.form['url']
            return redirect(f"/{user_url}")

        return render_template('home.html')

    @app.route('/<path:url>')
    def fetch_minimal_page(url):
        try:
            if not url.startswith('http'):
                full_url = f"http://{url}"
            else:
                full_url = url

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            markdown_text = loop.run_until_complete(render_page_and_extract_text(full_url))

            html_content = markdown.markdown(markdown_text)

            return render_template('rendered_page.html', content=html_content)

        except Exception as e:
            return jsonify({"error": str(e)}), 500

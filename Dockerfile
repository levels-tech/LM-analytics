# Use an official Python image (keep this unchanged unless you need a specific version)
FROM python:3.12-slim

# Set the working directory (keep this unless you want a different folder inside the container)
WORKDIR /app

# Copy all required files from your local folder to the Docker container (keep this line but ensure your app files are in the same directory as this Dockerfile)
COPY . /app

# Install Python dependencies (keep this unchanged, but make sure `requirements.txt` includes all your app's dependencies)
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port used by Streamlit (keep this unchanged unless you customize the Streamlit port)
EXPOSE 8501

# Run the Streamlit app (replace `your_app.py` with the filename of your Streamlit script)
CMD ["streamlit", "run", "lilmilan.py", "--server.headless=true"]

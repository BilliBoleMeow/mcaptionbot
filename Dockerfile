# Dockerfile

# 1. Base Image: Choose a Python version. 3.10-slim is a good balance.
FROM python:3.10-slim

# 2. Set Environment Variables
ENV PYTHONDONTWRITEBYTECODE 1 # Prevents python from writing .pyc files to disc
ENV PYTHONUNBUFFERED 1       # Force stdin, stdout and stderr to be totally unbuffered

# 3. Install System Dependencies (including mediainfo)
#    Update package lists and install mediainfo and any other system libs.
#    Clean up apt lists to reduce image size.
RUN apt-get update \
    && apt-get install -y --no-install-recommends mediainfo \
    && rm -rf /var/lib/apt/lists/*

# 4. Set the Working Directory in the container
WORKDIR /usr/src/app

# 5. Copy requirements.txt first to leverage Docker cache
#    If requirements.txt hasn't changed, this layer will be cached.
COPY requirements.txt ./

# 6. Install Python Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 7. Create necessary directories within the container
#    The TEMP_DOWNLOAD_DIR in config.py is set relative to the project root
#    which will be /usr/src/app in the container.
RUN mkdir -p /usr/src/app/temp_downloads

# 8. Copy the Bot Application Code
#    This copies everything in the 'bot' subdirectory from your host
#    into a 'bot' subdirectory in the container's WORKDIR (/usr/src/app/bot)
COPY ./bot ./bot

# 9. (Optional) Add a non-root user for security
# RUN addgroup --system app && adduser --system --group app
# USER app

# 10. Specify the Command to run the application
#     We use the module execution method which is good for packages.
CMD ["python", "-m", "bot.main"]
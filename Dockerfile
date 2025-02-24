# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install tzdata for timezone configuration
RUN apt-get update && apt-get install -y tzdata

# Set the timezone using an environment variable (replace with your timezone)
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 10691

# Run the python server.py module directly instead of uvicorn cli
CMD ["python", "server.py"]

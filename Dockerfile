# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 10691

# Use the host's time zone settings
RUN ln -sf /usr/share/zoneinfo/$(cat /etc/timezone) /etc/localtime

# Run the python server.py module directly instead of uvicorn cli
CMD ["python", "server.py"]

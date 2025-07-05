# Stage 1: Build stage
FROM python:3.11.7 AS builder

# Set the working directory
WORKDIR /usr/src/app

# Copy only the requirements file first to leverage Docker caching
COPY requirements.txt ./

# Install virtualenv
RUN pip install --no-cache-dir virtualenv

# Create a virtual environment
RUN virtualenv venv

# Install dependencies in the virtual environment
RUN ./venv/bin/pip install --no-cache-dir -r requirements.txt

# Install Gunicorn in the virtual environment
RUN ./venv/bin/pip install gunicorn

# Check if Gunicorn is installed using Python
RUN ./venv/bin/python -c "import gunicorn; print(gunicorn.__version__)"

# Copy the rest of the application code
COPY . .

# Apply migrations (optional, depends on your application needs)
#RUN ./venv/bin/python manage.py migrate

# Stage 2: Production stage
FROM python:3.11.7 AS runtime

# Set the working directory
WORKDIR /usr/src/app

# Copy the virtual environment and necessary files from the builder stage
COPY --from=builder /usr/src/app /usr/src/app

# Ensure that the virtual environment's bin directory is in the PATH
ENV PATH="/usr/src/app/venv/bin:${PATH}"

# Expose the port the app runs on
#EXPOSE 4016

# Start the application with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:4033", "smart_medical_scheduling.wsgi:application", "-c", "gunicorn_config.py"]



FROM python:3.13-alpine
WORKDIR /app
COPY app.py .
ENV PORT=8000
EXPOSE 8000
USER nobody
CMD ["python", "-u", "app.py"]

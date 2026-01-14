# Folder Descriptions

⚠️ Please make sure you update .env.example whenever you add a new environment variable. Also, update requirements.txt when you add a new python package.

## `frontend/`
Contains the source code for the client-side application in react. if you want to run, cd into the folder and run `npm install` followed by `npm run dev`.

## `backend/`
All the code, data and models for backend. This folder is sub-divided into following folders:
  - `src/`: all the api routes, business logic and database interactions are implemented here.
  - `milvus/`: Contains the collection schemas for vector db Milvus. Also contains scripts to fill the collection with data.
  - `neo4j/`: Contains schema for graph db, script to fill the database and fetech details needed for milvus collection.
  - `documents/`: Dummy data for development and testing.
  - `main.py`: The entry point for the FastAPI application to access all the backend services.
  - `requirements.txt`: Lists the Python dependencies required to run the backend application.
  - `README.md`: Documentation specific to the backend folder, providing instructions on setup, usage, and other relevant information.

# Problem Statement

## AI-Powered Restaurant Recommendation System (Zomato Use Case)

Build an AI-powered restaurant recommendation service inspired by Zomato. The system should intelligently suggest restaurants based on user preferences by combining structured restaurant data with a Large Language Model (LLM).

---

## Objective

Design and implement an application that:

- Takes user preferences (such as location, budget, cuisine, and ratings)
- Uses a real-world dataset of restaurants
- Leverages an LLM to generate personalized, human-like recommendations
- Displays clear and useful results to the user

---

## Dataset

- **Source:** [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) on Hugging Face
- **Relevant fields:** restaurant name, location, cuisine, cost, rating, and related attributes

---

## System Workflow

### 1. Data Ingestion

- Load and preprocess the Zomato dataset from Hugging Face
- Extract and normalize relevant fields (name, location, cuisine, cost, rating, etc.)

### 2. User Input

Collect user preferences:

| Preference | Examples |
|---|---|
| Location | Bangalore |
| Budget | low, medium, high |
| Cuisine | Italian, Chinese |
| Minimum rating | e.g. 4.0+ |
| Additional preferences | family-friendly, quick service |

### 3. Integration Layer

- Filter and prepare relevant restaurant data based on user input
- Pass structured results into an LLM prompt
- Design a prompt that helps the LLM reason about and rank options

### 4. Recommendation Engine

Use the LLM to:

- Rank restaurants
- Provide explanations for why each recommendation fits
- Optionally summarize the set of choices

### 5. Output Display

Present top recommendations in a user-friendly format, including:

- Restaurant name
- Cuisine
- Rating
- Estimated cost
- AI-generated explanation

---

## Project Context Summary

This project is a **retrieval-plus-reasoning** recommendation system:

1. **Structured filtering** narrows the restaurant corpus using explicit user constraints (location, budget, cuisine, rating).
2. **LLM reasoning** ranks the filtered candidates and produces natural-language justifications.
3. **UI presentation** surfaces ranked results with clear, actionable detail for the end user.

The goal is a practical Zomato-style experience where recommendations feel personalized and explainable, not just a static filter on a table of restaurants.

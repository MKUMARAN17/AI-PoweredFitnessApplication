# 🏋️‍♂️ AI-Powered Fitness Application (Backend)

In today's fast-paced world, maintaining fitness can be a challenge. This AI-powered fitness application aims to provide users with intelligent tracking and personalized recommendations to help them achieve their health goals. This repository contains the backend implementation, developed using a **Spring Boot microservices architecture** to ensure scalability, resilience, and ease of maintenance. The application leverages modern technologies like Keycloak for robust security, RabbitMQ for efficient asynchronous communication, and the Google Gemini API for intelligent fitness insights.

---

## 📌 Features

✅ User Authentication & Authorization using Spring Security for secure role-based access control.

🏃 Fitness Activity Tracking — logs user steps, calories, and workout duration.

🤖 AI-Powered Recommendations through Google Gemini API to deliver personalized health and fitness suggestions.

🔒 Secure REST APIs ensuring data protection and privacy across all microservices.

⚙️ Microservice Architecture using Spring Boot & Spring Cloud for scalable and maintainable backend services.

---

## 📂 Project Structure

AI-PoweredFitnessApplication/
│
├── activity-service/ --> Handles fitness activity logic (e.g., adding, retrieving activity logs)
├── auth-service/ --> Manages Keycloak authentication, user registration, and token management
├── ai-service/ --> Integrates with the Google Gemini API for generating intelligent recommendations
├── notification-service/ --> Manages message publishing and listening with RabbitMQ for asynchronous user updates
├── common-utils/ --> Contains shared resources, utilities, and models across all services
└── README.md --> This file


---

## 🚀 Getting Started

### Prerequisites

-   **Java 17 or higher**: The runtime environment for Spring Boot applications.
-   **Maven 3.6+**: For building and managing project dependencies.
-   **Docker**: Essential for easily running RabbitMQ and optionally Keycloak.
-   **Google Gemini API Key**: Required for the AI-powered recommendation service.

---

### 🔧 Setup Instructions

#### 1. Clone the Repository

```bash
git clone [https://github.com/](https://github.com/)[YOUR_USERNAME]/AI-PoweredFitnessApplication.git
cd AI-PoweredFitnessApplication
2. Start RabbitMQ in Docker
Bash

docker run -d --hostname rabbitmq --name rabbitmq \
  -p 5672:5672 -p 15672:15672 rabbitmq:3-management
This command starts a RabbitMQ container with the management plugin enabled, accessible via http://localhost:15672.

3. Configure Environment Variables
Create a .env file in the root directory of the project, or configure these variables directly in your IDE's run configurations:

GOOGLE_GEMINI_API_KEY=[YOUR_GOOGLE_GEMINI_API_KEY]
KEYCLOAK_SERVER_URL=http://localhost:8080
RABBITMQ_HOST=localhost
4. Build and Run Each Service
Navigate to each service directory and use Maven to start them. You will need to run each service in a separate terminal window or process.

Bash

cd activity-service
mvn spring-boot:run
Repeat for each of the following:

auth-service

ai-service

notification-service

📬 API Overview
Auth Service
POST /auth/register – Register a new user account.

POST /auth/login – Authenticate and retrieve an access token for subsequent API calls.

Activity Service
POST /activities/add – Add a new fitness activity record (e.g., steps, calories burned, workout duration).

GET /activities/user/{userId} – Retrieve all activity logs for a specific user.

AI Service
POST /ai/suggestions – Generate personalized workout suggestions or nutritional advice based on user data.

Notification Service
This service primarily functions as a RabbitMQ listener for user updates and messages, enabling asynchronous processing of notifications and internal service communications.

🧰 Tech Stack
Java 17: Core programming language.

Spring Boot: Framework for building robust, production-ready applications.

Spring Security + Keycloak: For comprehensive authentication and authorization.

RabbitMQ: Message broker for asynchronous communication.

Google Gemini API: For AI-powered recommendations.

Maven: Project management and build automation tool.

Docker: Containerization platform for easy deployment of dependencies.

👨‍💻 Author
Muthukumaran M

🔗 LinkedIn: linkedin.com/in/muthukumaran-m-529026285

💻 GitHub: MKUMARAN17

📜 License
This project is licensed under the MIT License. See the LICENSE file for more details.

🙌 Acknowledgements
Spring Boot: For simplifying Java development.

Keycloak: For open-source identity and access management.

Google Gemini: For powerful AI capabilities.

RabbitMQ: For reliable messaging.

🚀 Future Enhancements
We are continuously working to improve this application. Planned enhancements include:

Integration of Swagger/OpenAPI documentation for all REST APIs.

A Docker Compose file for simplified one-command deployment of all services and dependencies.

Details and setup instructions for the frontend repository once available.

Additional AI models for more diverse recommendations (e.g., diet plans, recovery tips).

# 🏋️‍♂️ AI-Powered Fitness Application

Welcome to the AI-Powered Fitness Application! This project provides users with intelligent tracking and personalized fitness recommendations to help them achieve their health goals. It features a robust **Spring Boot microservices architectecture** on the backend and a modern **React + Vite** application on the frontend. The application uses JWT for secure authentication, MySQL and MongoDB for fast data storage, and the **OpenAI API** / **Google Gemini API** for intelligent fitness insights.

---

## 📌 Features

- ✅ **User Authentication & Authorization**: Custom JWT-based authentication with Refresh Token support via Spring Cloud Gateway.
- 🏃 **Fitness Activity Tracking**: Comprehensive logging of user activities (Steps, Calories, Workout Duration) per user.
- 🤖 **AI-Powered Recommendations**: Delivers personalized workout and nutrition suggestions based on user data using external Large Language Models (LLMs).
- 🔒 **Secure REST APIs**: Protects endpoints with industry-standard security practices and Gateway-level JWT filtering.
- ⚙️ **Microservice Architecture**: Decoupled backend services for Auth/Users, Activities, AI Recommendations, and an API Gateway for routing.
- 🎨 **Modern Frontend**: Responsive and dynamic user interface built with React, Tailwind CSS, and Framer Motion.

---

## 📂 Project Structure

```text
AI-PoweredFitnessApplication/
│
├── frontend/             --> React + Vite frontend application (running on port 5173)
├── gateway/              --> Spring Cloud API Gateway handling routing and JWT validation (port 8090)
├── userservice/          --> Manages user accounts, profiles, and JWT authentication (port 8081)
├── activityservice/      --> Handles fitness activity logs and metrics (port 8082)
├── aiservice/            --> Integrates with LLMs for generating intelligent recommendations (port 8083)
└── README.md             --> This file
```

---

## 🧰 Tech Stack

**Frontend Framework & Libraries:**
- React 19, Vite, Tailwind CSS 4, Framer Motion, Axios, React Router v7

**Backend Languages & Frameworks:**
- Java 21, Spring Boot 3.4.x, Spring Cloud Gateway

**Databases:**
- **MySQL 8**: Relational storage for User Accounts and Authentication data (`userservice`).
- **MongoDB**: NoSQL storage for flexible Activity Logs (`activityservice`) and AI suggestions (`aiservice`).

**Security & External APIs:**
- JSON Web Tokens (JJWT)
- OpenAI API (or Google Gemini API)

---

## 🚀 Getting Started

### Prerequisites

- **Java 21**: The runtime environment for the backend services.
- **Node.js (v18+) and npm**: Core runtime for running the frontend Vite server.
- **Gradle**: For building and managing backend dependencies.
- **MySQL Server**: Running on `localhost:3306`. Create a database named `fitness_user_Db`.
- **MongoDB**: Running on `localhost:27017`.
- **OpenAI/Gemini API Key**: Required for the AI-powered recommendation service.

---

### 🔧 Setup Instructions

#### 1. Clone the Repository

```bash
git clone https://github.com/MKUMARAN17/AI-PoweredFitnessApplication.git
cd AI-PoweredFitnessApplication
```

#### 2. Configure Databases
Ensure that your local **MySQL** server has a database named `fitness_user_Db` with the root user credentials (or update them in the `userservice/src/main/resources/application.yml`).
Ensure that your local **MongoDB** is running on the default port (`27017`).

#### 3. Configure Environment Variables
If required, configure these variables directly in your IDE's run configurations or export them:
- `OPENAI_API_KEY`: Set this to your valid OpenAI/Gemini API key for the AI Service.

#### 4. Build and Run Backend Services
Navigate to each service directory and use Gradle to start them. You can run each in a separate terminal:

```bash
# Start User Service
cd userservice
./gradlew bootRun

# Start Activity Service
cd ../activityservice
./gradlew bootRun

# Start AI Service
cd ../aiservice
export OPENAI_API_KEY="your_api_key_here"  # Provide your valid key
./gradlew bootRun

# Start API Gateway (Must run on port 8090)
cd ../gateway
./gradlew bootRun
```

#### 5. Build and Run Frontend
The frontend requires Node modules to be installed first.

```bash
cd frontend
npm install
npm run dev
```

The frontend application should now be accessible at `http://localhost:5173`.

---

## 📬 API Overview (Through API Gateway)

The API Gateway runs on `localhost:8090` and routes traffic to the backend services.

- **Auth & Users (`/api/users/**`)**
  - Directed to `userservice`.
  - Registration, Login, and fetching user data. Includes JWT generation.
  
- **Activities (`/api/activities/**`)**
  - Directed to `activityservice`.
  - Add and retrieve fitness activity logs for users.

- **AI Recommendations (`/api/recommendations/**`)**
  - Directed to `aiservice`.
  - Generate personalized workout and AI Coach suggestions based on user context.

---

## 👨‍💻 Author

**Muthukumaran M**
- 💻 GitHub: [MKUMARAN17](https://github.com/MKUMARAN17)

## 📜 License
This project is licensed under the MIT License. See the LICENSE file for more details.

## 🙌 Acknowledgements
- **Spring Boot & Spring Cloud**: For simplifying microservices construction.
- **React & Vite**: For lightning-fast frontend development.
- **Tailwind CSS**: For effortless utility-first styling.
- **OpenAI / Google Gemini**: For powerful AI capabilities.

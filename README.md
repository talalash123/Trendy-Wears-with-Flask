TrendyWears – Online Clothing Shopping Website

1. Overview

TrendyWears is a full-stack online clothing shopping website that allows users to browse, purchase, and manage clothing items through a modern web interface. The platform includes separate modules for customers and administrators, providing a complete e-commerce experience.

2. Features
Customer Module
User registration and login
Browse products by category (Men / Women)
Add products to cart
Purchase products (Buy Now)
View purchase history (Delivered orders only)
Admin Module
Admin login
Add new clothing products
View and manage products
Manage customer orders
Mark orders as delivered

3. Technologies Used
Frontend: HTML, CSS, JavaScript, Bootstrap
Backend: Flask (Python)
Database: MongoDB
Tools: Visual Studio Code

4. System Workflow
Customer Side
User registers or logs into the system
Browses products based on categories
Adds items to cart or directly purchases
Enters delivery details (name and address)
Views purchase history after delivery
Admin Side
Admin logs into the dashboard
Adds and manages products
Views customer orders
Marks orders as delivered

5. Project Structure
TrendyWears/

├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── css/
│   └── js/

├── backend/
│   ├── app.py
│   ├── routes/
│   ├── models/
│   └── database/

└── README.md

6. Installation and Setup
6.1 Clone the Repository
git clone https://github.com/your-username/trendywears.git
6.2 Backend Setup
pip install flask pymongo
python app.py
6.3 Database Setup
Install and start MongoDB
Create database: trendywears_db
6.4 Run the Project
Open frontend in browser
Or connect frontend with Flask backend routes

7. Future Enhancements
Payment gateway integration
Product search and filters
User profile system
Order tracking feature
Mobile responsive UI

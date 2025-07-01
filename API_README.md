# RESTful API Documentation

This document provides an overview of the RESTful API for the Electronic Products E-Commerce platform.

## Overview

The API allows interaction with the platform's resources including:
- Products
- Categories
- Users/Authentication
- Orders
- Cart

## Authentication

Most API endpoints require authentication using JWT (JSON Web Token). To authenticate:

1. Send a POST request to `/api/auth/login` with your email and password:
   ```json
   {
     "email": "user@example.com",
     "password": "password"
   }
   ```

2. The API will respond with an access token:
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "user_id": 1
   }
   ```

3. Include this token in the Authorization header for subsequent requests:
   ```
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

## API Endpoints

### Products

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/products` | Get all products | No |
| GET | `/api/products?category=1&search=keyword` | Filter products by category and/or search term | No |
| GET | `/api/products/{product_id}` | Get a specific product | No |
| POST | `/api/products` | Create a new product | Yes (Admin) |
| PUT | `/api/products/{product_id}` | Update a product | Yes (Admin) |
| DELETE | `/api/products/{product_id}` | Delete a product | Yes (Admin) |

### Categories

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/categories` | Get all categories | No |
| GET | `/api/categories/{category_id}` | Get a specific category | No |
| POST | `/api/categories` | Create a new category | Yes (Admin) |
| PUT | `/api/categories/{category_id}` | Update a category | Yes (Admin) |
| DELETE | `/api/categories/{category_id}` | Delete a category | Yes (Admin) |

### User Profile

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/users/profile` | Get current user profile | Yes |
| PUT | `/api/users/profile` | Update user profile | Yes |

### Orders

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/orders` | Get user orders | Yes |
| GET | `/api/orders/{order_id}` | Get specific order details | Yes |
| POST | `/api/orders` | Create a new order | Yes |

### Cart

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/cart` | Get user cart | Yes |
| POST | `/api/cart/add` | Add item to cart | Yes |
| PUT | `/api/cart/update` | Update cart items | Yes |
| DELETE | `/api/cart/clear` | Clear user cart | Yes |

## Using Swagger UI

A Swagger UI interface is available to explore and test the API:

1. Start the application
2. Navigate to `/api/docs` in your browser
3. Explore available endpoints and test them directly from the UI

## Example API Calls

### Get All Products

```bash
curl -X GET http://localhost:5000/api/products
```

### Get Product by ID

```bash
curl -X GET http://localhost:5000/api/products/1
```

### Login

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

### Create Product (Admin only)

```bash
curl -X POST http://localhost:5000/api/products \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Product",
    "description": "Product description",
    "price": 99.99,
    "stock": 10,
    "category_id": 1
  }'
```

### Add to Cart

```bash
curl -X POST http://localhost:5000/api/cart/add \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 2
  }' 
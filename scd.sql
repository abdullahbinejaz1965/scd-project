-- create database
CREATE DATABASE employee_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- create app user (safer than using root)
CREATE USER 'appuser'@'localhost' IDENTIFIED BY 'StrongPasswordHere!';
GRANT ALL PRIVILEGES ON employee_db.* TO 'appuser'@'localhost';
FLUSH PRIVILEGES;

-- tables
USE employee_db;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL
);

CREATE TABLE employees (
  id INT PRIMARY KEY,               -- you pass id from form in your code
  name VARCHAR(150) NOT NULL,
  email VARCHAR(150) NOT NULL,
  year_of_birth INT,
  qualification VARCHAR(150),
  salary DECIMAL(10,2),
  job_title VARCHAR(150),
  date_of_joining DATE,
  department VARCHAR(150),
  status VARCHAR(50)
);

CREATE TABLE inventory (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  quantity INT NOT NULL,
  description TEXT
);

CREATE TABLE employee_inventory (
  id INT AUTO_INCREMENT PRIMARY KEY,
  employee_id INT,
  inventory_id INT,
  assigned_date DATE,
  FOREIGN KEY (employee_id) REFERENCES employees(id),
  FOREIGN KEY (inventory_id) REFERENCES inventory(id)
);
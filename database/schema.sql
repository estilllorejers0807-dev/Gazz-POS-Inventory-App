CREATE DATABASE IF NOT EXISTS `gazz_pos_inventory`;
USE `gazz_pos_inventory`;

CREATE TABLE IF NOT EXISTS `users` (
  `user_id` INT AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(50) UNIQUE NOT NULL,
  `full_name` VARCHAR(100) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `role` ENUM('admin', 'manager', 'cashier') NOT NULL DEFAULT 'cashier',
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `products` (
  `product_id` INT AUTO_INCREMENT PRIMARY KEY,
  `product_name` VARCHAR(100) NOT NULL,
  `cost_price` DECIMAL(10,2) NOT NULL,
  `selling_price` DECIMAL(10,2) NOT NULL,
  `low_stock_threshold` INT DEFAULT 10,
  `is_active` TINYINT(1) DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `inventory` (
  `inventory_id` INT AUTO_INCREMENT PRIMARY KEY,
  `product_id` INT UNIQUE NOT NULL,
  `stock_quantity` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`product_id`) REFERENCES `products`(`product_id`) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS `fuel_pumps` (
  `pump_id` INT AUTO_INCREMENT PRIMARY KEY,
  `pump_name` VARCHAR(50) NOT NULL,
  `product_id` INT NOT NULL,
  `is_active` TINYINT(1) DEFAULT 1,
  FOREIGN KEY (`product_id`) REFERENCES `products`(`product_id`)
);

CREATE TABLE IF NOT EXISTS `sales` (
  `sale_id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `system_type` ENUM('convenience', 'gasoline') NOT NULL,
  `total_amount` DECIMAL(10,2) NOT NULL,
  `status` ENUM('completed', 'cancelled') DEFAULT 'completed',
  `sale_date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`)
);

CREATE TABLE IF NOT EXISTS `sale_items` (
  `item_id` INT AUTO_INCREMENT PRIMARY KEY,
  `sale_id` INT NOT NULL,
  `product_id` INT NOT NULL,
  `pump_id` INT NULL,
  `quantity` DECIMAL(10,2) NOT NULL,
  `cost_price` DECIMAL(10,2) NOT NULL,
  `unit_price` DECIMAL(10,2) NOT NULL,
  `subtotal` DECIMAL(10,2) NOT NULL,
  FOREIGN KEY (`sale_id`) REFERENCES `sales`(`sale_id`) ON DELETE CASCADE,
  FOREIGN KEY (`product_id`) REFERENCES `products`(`product_id`),
  FOREIGN KEY (`pump_id`) REFERENCES `fuel_pumps`(`pump_id`)
);
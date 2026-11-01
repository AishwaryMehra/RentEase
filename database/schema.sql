-- ============================================================
-- RentEase Rental Portal | Database Schema
-- Engine: InnoDB | Charset: utf8mb4
-- Aligns with UN SDG 11: Sustainable Cities and Communities
-- ============================================================

-- Create and select the database
CREATE DATABASE IF NOT EXISTS rental_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE rental_db;

-- ============================================================
-- TABLE: users
-- Stores both tenant and owner accounts with hashed passwords
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    user_id       INT            NOT NULL AUTO_INCREMENT,
    full_name     VARCHAR(100)   NOT NULL,
    email         VARCHAR(100)   NOT NULL,
    password_hash VARCHAR(255)   NOT NULL,
    phone         VARCHAR(15)    NOT NULL,
    role          ENUM('tenant', 'owner') NOT NULL,
    created_at    TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_id),
    UNIQUE KEY uq_users_email (email),
    INDEX idx_users_role (role)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- TABLE: properties
-- Each listing is owned by a user with role='owner'
-- Cascades deletions from users -> properties
-- ============================================================
CREATE TABLE IF NOT EXISTS properties (
    property_id       INT              NOT NULL AUTO_INCREMENT,
    owner_id          INT              NOT NULL,
    title             VARCHAR(150)     NOT NULL,
    description       TEXT,
    property_type     ENUM('Apartment', 'Independent House', 'Villa', 'Studio', 'PG') NOT NULL,
    address           TEXT             NOT NULL,
    city              VARCHAR(50)      NOT NULL,
    rent_monthly      DECIMAL(10, 2)   NOT NULL,
    security_deposit  DECIMAL(10, 2)   NOT NULL,
    bedrooms          INT              NOT NULL,
    bathrooms         INT              NOT NULL,
    furnishing_status ENUM('Furnished', 'Semi-Furnished', 'Unfurnished') NOT NULL,
    is_available      BOOLEAN          NOT NULL DEFAULT TRUE,
    image_url         VARCHAR(500)     NOT NULL DEFAULT 'https://images.unsplash.com/photo-1560518883-ce09059eeffa',
    created_at        TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (property_id),
    CONSTRAINT fk_properties_owner
        FOREIGN KEY (owner_id) REFERENCES users (user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    INDEX idx_properties_city         (city),
    INDEX idx_properties_owner_id     (owner_id),
    INDEX idx_properties_is_available (is_available),
    INDEX idx_properties_rent         (rent_monthly)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- TABLE: rental_requests
-- Tenants submit requests against available properties
-- Cascades deletions from both users and properties
-- ============================================================
CREATE TABLE IF NOT EXISTS rental_requests (
    request_id           INT      NOT NULL AUTO_INCREMENT,
    property_id          INT      NOT NULL,
    tenant_id            INT      NOT NULL,
    message              TEXT,
    proposed_move_in_date DATE    NOT NULL,
    status               ENUM('Pending', 'Approved', 'Rejected', 'Cancelled') NOT NULL DEFAULT 'Pending',
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (request_id),
    CONSTRAINT fk_requests_property
        FOREIGN KEY (property_id) REFERENCES properties (property_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_requests_tenant
        FOREIGN KEY (tenant_id) REFERENCES users (user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    INDEX idx_requests_tenant_id   (tenant_id),
    INDEX idx_requests_property_id (property_id),
    INDEX idx_requests_status      (status)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- Run this in Supabase SQL editor to add the employee onboarding tables
-- Safe to run multiple times (IF NOT EXISTS / IF NULL guards)

-- ─────────────────────────────────────────────────────────────
-- 1. Department table (employees will FK to it)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS department (
    id SERIAL PRIMARY KEY,
    department_name VARCHAR(255) NOT NULL
);

-- ─────────────────────────────────────────────────────────────
-- 2. Add columns to employees table
-- ─────────────────────────────────────────────────────────────
ALTER TABLE employees
    ADD COLUMN IF NOT EXISTS end_date DATE,
    ADD COLUMN IF NOT EXISTS remark VARCHAR(255),
    ADD COLUMN IF NOT EXISTS department_id INTEGER REFERENCES department(id);

-- Make job_title nullable (register flow doesn't provide it)
ALTER TABLE employees ALTER COLUMN job_title DROP NOT NULL;

-- ─────────────────────────────────────────────────────────────
-- 3. Expand user_financial_info with all salary / bank fields
-- ─────────────────────────────────────────────────────────────
ALTER TABLE user_financial_info
    ADD COLUMN IF NOT EXISTS employment_type    VARCHAR(50),
    ADD COLUMN IF NOT EXISTS salary_basic       INTEGER,
    ADD COLUMN IF NOT EXISTS salary_gross       INTEGER,
    ADD COLUMN IF NOT EXISTS salary_net         INTEGER,
    ADD COLUMN IF NOT EXISTS salary_balance     INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS trip_balance       INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS allowance_house_rent   INTEGER,
    ADD COLUMN IF NOT EXISTS allowance_medical      INTEGER,
    ADD COLUMN IF NOT EXISTS allowance_special      INTEGER,
    ADD COLUMN IF NOT EXISTS allowance_fuel         INTEGER,
    ADD COLUMN IF NOT EXISTS allowance_phone_bill   INTEGER,
    ADD COLUMN IF NOT EXISTS allowance_other        INTEGER,
    ADD COLUMN IF NOT EXISTS allowance_total        INTEGER,
    ADD COLUMN IF NOT EXISTS deduction_provident_fund INTEGER,
    ADD COLUMN IF NOT EXISTS deduction_tax          INTEGER,
    ADD COLUMN IF NOT EXISTS deduction_other        INTEGER,
    ADD COLUMN IF NOT EXISTS deduction_total        INTEGER,
    ADD COLUMN IF NOT EXISTS bank_name          VARCHAR(255),
    ADD COLUMN IF NOT EXISTS account_name       VARCHAR(255),
    ADD COLUMN IF NOT EXISTS account_number     VARCHAR(255),
    ADD COLUMN IF NOT EXISTS iban               VARCHAR(255),
    ADD COLUMN IF NOT EXISTS start_date         DATE,
    ADD COLUMN IF NOT EXISTS end_date           DATE,
    ADD COLUMN IF NOT EXISTS esic_status        VARCHAR(3) NOT NULL DEFAULT 'No';

-- ─────────────────────────────────────────────────────────────
-- 4. user_personal_info table
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_personal_info (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER REFERENCES employees(id) ON DELETE CASCADE,
    date_of_birth  DATE,
    gender         VARCHAR(10),
    marital_status VARCHAR(20),
    father_name    VARCHAR(255),
    id_number      VARCHAR(255),
    address        VARCHAR(500),
    city           VARCHAR(255),
    state          VARCHAR(255),
    country        VARCHAR(255),
    mobile         VARCHAR(50),
    phone          VARCHAR(50),
    email_address  VARCHAR(255)
);

-- ─────────────────────────────────────────────────────────────
-- 5. employee table  (govt IDs — different from 'employees')
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS employee (
    id               INTEGER PRIMARY KEY
                         REFERENCES employees(id) ON DELETE CASCADE ON UPDATE CASCADE,
    email_address    VARCHAR(255),
    aadhaar_number   VARCHAR(25),
    pan_number       VARCHAR(25),
    esic_number      VARCHAR(25),
    pf_number        VARCHAR(25),
    nominee_name     VARCHAR(255),
    nominee_relation VARCHAR(255)
);

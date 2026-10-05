-- ==============================================================================
-- AI Personal Finance Coach — Initial Database Schema
-- Migration: 20261005000000_init_schema.sql
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Profiles Table
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL, -- References auth.users(id) in Supabase Auth
    age INTEGER NOT NULL CHECK (age >= 18 AND age <= 120),
    annual_income NUMERIC(14, 2) NOT NULL CHECK (annual_income >= 0),
    monthly_expenses NUMERIC(14, 2) NOT NULL CHECK (monthly_expenses >= 0),
    savings NUMERIC(14, 2) NOT NULL DEFAULT 0.00 CHECK (savings >= 0),
    investments NUMERIC(14, 2) NOT NULL DEFAULT 0.00 CHECK (investments >= 0),
    debt NUMERIC(14, 2) NOT NULL DEFAULT 0.00 CHECK (debt >= 0),
    debt_details JSONB DEFAULT '[]'::JSONB,
    risk_appetite VARCHAR(20) NOT NULL CHECK (risk_appetite IN ('conservative', 'moderate', 'aggressive')),
    investment_horizon_years INTEGER NOT NULL CHECK (investment_horizon_years >= 0),
    retirement_age_target INTEGER NOT NULL CHECK (retirement_age_target > age),
    primary_goal TEXT NOT NULL,
    monthly_investment_capacity NUMERIC(14, 2) NOT NULL CHECK (monthly_investment_capacity >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Plans Table
CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'archived', 'fallback')),
    health_summary TEXT NOT NULL,
    actions JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plans_user_status ON plans(user_id, status);

-- 3. Plan Evaluations (HHH Audit Log)
CREATE TABLE IF NOT EXISTS plan_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    iteration INTEGER NOT NULL DEFAULT 0,
    helpful_score INTEGER NOT NULL CHECK (helpful_score BETWEEN 0 AND 4),
    honest_score INTEGER NOT NULL CHECK (honest_score BETWEEN 0 AND 4),
    harmless_score INTEGER NOT NULL CHECK (harmless_score BETWEEN 0 AND 4),
    passed BOOLEAN NOT NULL,
    critical_issue BOOLEAN NOT NULL DEFAULT FALSE,
    critique TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evaluations_plan_id ON plan_evaluations(plan_id);

-- 4. Action Feedback Table
CREATE TABLE IF NOT EXISTS action_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(user_id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    action_id VARCHAR(100) NOT NULL,
    outcome VARCHAR(20) NOT NULL CHECK (outcome IN ('worked', 'did_not_work')),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_user_created ON action_feedback(user_id, created_at DESC);

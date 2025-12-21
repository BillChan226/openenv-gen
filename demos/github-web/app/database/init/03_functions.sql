-- Utility functions for {{ENV_NAME}}

-- Function to reset database to initial state (for environment resets)
CREATE OR REPLACE FUNCTION reset_environment() RETURNS void AS $$
BEGIN
    -- Truncate all tables except Users
    -- {{GENERATED_TRUNCATE_STATEMENTS}}

    -- Reset sequences
    -- {{GENERATED_SEQUENCE_RESETS}}

    -- Re-seed data
    -- This would be called from the environment reset

    RAISE NOTICE 'Environment reset complete';
END;
$$ LANGUAGE plpgsql;

-- Function to get environment state (for reward computation)
CREATE OR REPLACE FUNCTION get_environment_state() RETURNS jsonb AS $$
DECLARE
    result jsonb;
BEGIN
    result := jsonb_build_object(
        'user_count', (SELECT COUNT(*) FROM "Users"),
        'timestamp', CURRENT_TIMESTAMP
        -- {{GENERATED_STATE_FIELDS}}
    );
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- {{GENERATED_FUNCTIONS}}

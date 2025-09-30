

CREATE TABLE "google-manager".public.cloud_status (
                              id SERIAL PRIMARY KEY,
                              pad_code VARCHAR(100) NOT NULL UNIQUE,
                              current_status VARCHAR(200),
                              number_of_run INT DEFAULT 0,
                              phone_number_counts INT DEFAULT 0,
                              country VARCHAR(100),
                              temple_id INT,
                              code varchar(100),
                              latitude float,
                              proxy VARCHAR(100),
                              longitude float,
                              language VARCHAR(100),
                              time_zone VARCHAR(100),
                              forward_num INT NOT NULL DEFAULT 0,
                              secondary_email_num INT NOT NULL DEFAULT 0,
                              is_secondary_email BOOLEAN NOT NULL DEFAULT false,
                              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                              num_of_error INT NOT NULL DEFAULT 0,
                              num_of_success INT NOT NULL DEFAULT 0,
                              num_other_error INT NOT NULL DEFAULT 0,
                              proxy_platform TEXT,
                              pad_name TEXT
);

CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 创建触发器
CREATE TRIGGER update_cloud_status_updated_at
    BEFORE UPDATE ON "google-manager".public.cloud_status
    FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
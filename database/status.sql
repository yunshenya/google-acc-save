

CREATE TABLE cloud_status (
                              id SERIAL PRIMARY KEY,
                              pad_code VARCHAR(100) NOT NULL UNIQUE,
                              current_status VARCHAR(200),
                              number_of_run INT DEFAULT 0,
                              phone_number_counts INT DEFAULT 0,
                              country VARCHAR(100),
                              temple_id INT NOT NULL,
                              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    BEFORE UPDATE ON cloud_status
    FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

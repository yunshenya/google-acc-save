

CREATE TABLE cloud_status (
                                id SERIAL PRIMARY KEY,
                                pad_code VARCHAR(100) NOT NULL UNIQUE,
                                current_status VARCHAR(200),
                                number_of_run INT default 0,
                                phone_number_counts INT default 0,
                                country VARCHAR(100),
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



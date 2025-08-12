

CREATE TABLE cloud_status (
                                id SERIAL PRIMARY KEY,
                                pad_code VARCHAR(100) NOT NULL UNIQUE,
                                current_status VARCHAR(200) NOT NULL,
                                number_of_run INT NOT NULL,
                                phone_number INT not null,
                                country VARCHAR(100) NOT NULL,
                                create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



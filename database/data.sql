create database "google-manager";

CREATE TABLE google_account (
                                id SERIAL PRIMARY KEY,
                                account VARCHAR(50) NOT NULL UNIQUE,
                                password VARCHAR(100) NOT NULL,
                                type INT DEFAULT 0,
                                status INT DEFAULT 0,
                                code VARCHAR(32),
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                for_email TEXT,
                                for_password TEXT,
                                is_boned_secondary_email boolean NOT NULL DEFAULT false
);

ALTER TABLE google_account OWNER TO postgres;
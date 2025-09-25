CREATE TABLE proxy_collection (
                                id SERIAL PRIMARY KEY,
                                country TEXT,
                                android_version TEXT,
                                temple_id INT,
                                code TEXT,
                                latitude float,
                                proxy TEXT,
                                longitude float,
                                language TEXT,
                                time_zone TEXT,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE proxy_collection OWNER TO postgres;
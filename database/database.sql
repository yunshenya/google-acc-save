-- Create the database
CREATE DATABASE "google-manager";

-- Connect to the database
\c "google-manager";

-- Set timezone to Shanghai (Asia/Shanghai)
SET timezone = 'Asia/Shanghai';

-- Make Shanghai timezone the default for this database
ALTER DATABASE "google-manager" SET timezone = 'Asia/Shanghai';
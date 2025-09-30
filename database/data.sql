-- Create the google_account table
CREATE TABLE "google-manager".public.google_account (
                                id SERIAL PRIMARY KEY,
                                account VARCHAR(50) NOT NULL UNIQUE,
                                password VARCHAR(100) NOT NULL,
                                type INT DEFAULT 0,
                                status INT DEFAULT 2,
                                code VARCHAR(32),
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                for_email TEXT,
                                for_password TEXT,
                                is_boned_secondary_email BOOLEAN NOT NULL DEFAULT false,
                                proxy_platform TEXT,
                                image_base64 TEXT,
                                is_forward_email BOOLEAN NOT NULL DEFAULT false
);

-- Set table owner
ALTER TABLE "google-manager".public.google_account OWNER TO postgres;

-- Verify timezone setting
SHOW timezone;

-- Add some helpful comments
COMMENT ON TABLE "google-manager".public.google_account IS 'Google账户管理表';
COMMENT ON COLUMN "google-manager".public.google_account.id IS '主键ID';
COMMENT ON COLUMN "google-manager".public.google_account.account IS 'Google账户名';
COMMENT ON COLUMN "google-manager".public.google_account.password IS '账户密码';
COMMENT ON COLUMN "google-manager".public.google_account.type IS '账户类型 (0=默认)';
COMMENT ON COLUMN "google-manager".public.google_account.status IS '账户状态 (0=默认)';
COMMENT ON COLUMN "google-manager".public.google_account.code IS '验证码或其他代码';
COMMENT ON COLUMN "google-manager".public.google_account.created_at IS '创建时间 (上海时区)';
COMMENT ON COLUMN "google-manager".public.google_account.for_email IS '关联邮箱';
COMMENT ON COLUMN "google-manager".public.google_account.for_password IS '关联密码';
COMMENT ON COLUMN "google-manager".public.google_account.is_boned_secondary_email IS '是否绑定辅助邮箱';

-- Create an index on account for faster lookups
CREATE INDEX idx_google_account_account ON "google-manager".public.google_account(account);
CREATE INDEX idx_google_account_status ON "google-manager".public.google_account(status);
CREATE INDEX idx_google_account_created_at ON "google-manager".public.google_account(created_at);
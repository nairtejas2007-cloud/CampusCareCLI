CREATE DATABASE IF NOT EXISTS campuscare
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE campuscare;

CREATE TABLE IF NOT EXISTS departments (
    department_id INT AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(500)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'faculty', 'admin') NOT NULL,
    department_id INT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_users_user_department (user_id, department_id),

    CONSTRAINT fk_users_department
        FOREIGN KEY (department_id)
        REFERENCES departments (department_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT chk_faculty_has_department
        CHECK (role <> 'faculty' OR department_id IS NOT NULL)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS complaint_categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    default_department_id INT NULL,

    CONSTRAINT fk_categories_default_department
        FOREIGN KEY (default_department_id)
        REFERENCES departments (department_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS complaints (
    complaint_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    category_id INT NOT NULL,
    assigned_department_id INT NULL,
    assigned_staff_id INT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR(200) NULL,
    priority ENUM('Low', 'Normal', 'High') NOT NULL DEFAULT 'Normal',
    status ENUM(
        'Submitted',
        'Under Review',
        'In Progress',
        'Resolved',
        'Rejected'
    ) NOT NULL DEFAULT 'Submitted',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,

    UNIQUE KEY uq_complaints_id_student (complaint_id, student_id),

    CONSTRAINT fk_complaints_student
        FOREIGN KEY (student_id)
        REFERENCES users (user_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_complaints_category
        FOREIGN KEY (category_id)
        REFERENCES complaint_categories (category_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_complaints_department
        FOREIGN KEY (assigned_department_id)
        REFERENCES departments (department_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_complaints_staff_department
        FOREIGN KEY (assigned_staff_id, assigned_department_id)
        REFERENCES users (user_id, department_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT chk_complaint_staff_has_department
        CHECK (
            assigned_staff_id IS NULL
            OR assigned_department_id IS NOT NULL
        ),

    CONSTRAINT chk_complaint_title_not_blank
        CHECK (CHAR_LENGTH(TRIM(title)) > 0),

    CONSTRAINT chk_complaint_description_not_blank
        CHECK (CHAR_LENGTH(TRIM(description)) > 0)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS complaint_updates (
    update_id INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id INT NOT NULL,
    updated_by INT NOT NULL,
    old_status ENUM(
        'Submitted',
        'Under Review',
        'In Progress',
        'Resolved',
        'Rejected'
    ) NULL,
    new_status ENUM(
        'Submitted',
        'Under Review',
        'In Progress',
        'Resolved',
        'Rejected'
    ) NOT NULL,
    remarks VARCHAR(1000) NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_updates_complaint
        FOREIGN KEY (complaint_id)
        REFERENCES complaints (complaint_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_updates_user
        FOREIGN KEY (updated_by)
        REFERENCES users (user_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id INT NOT NULL UNIQUE,
    student_id INT NOT NULL,
    rating TINYINT NOT NULL,
    issue_fixed BOOLEAN NOT NULL,
    comments VARCHAR(1000) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_feedback_student
        FOREIGN KEY (student_id)
        REFERENCES users (user_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT fk_feedback_complaint_owner
        FOREIGN KEY (complaint_id, student_id)
        REFERENCES complaints (complaint_id, student_id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    CONSTRAINT chk_feedback_rating
        CHECK (rating BETWEEN 1 AND 5)
) ENGINE=InnoDB;

INSERT INTO departments (department_name, description)
SELECT 'IT Department', 'Handles Wi-Fi and internet complaints.'
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM departments WHERE department_name = 'IT Department'
);

INSERT INTO departments (department_name, description)
SELECT 'Canteen Administration', 'Handles food and canteen complaints.'
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM departments
    WHERE department_name = 'Canteen Administration'
);

INSERT INTO departments (department_name, description)
SELECT 'Academic Administration', 'Handles faculty and teaching complaints.'
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM departments
    WHERE department_name = 'Academic Administration'
);

INSERT INTO departments (department_name, description)
SELECT 'Maintenance Department', 'Handles classroom and equipment complaints.'
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM departments
    WHERE department_name = 'Maintenance Department'
);

INSERT INTO departments (department_name, description)
SELECT 'Housekeeping', 'Handles cleanliness and sanitation complaints.'
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM departments WHERE department_name = 'Housekeeping'
);

INSERT INTO departments (department_name, description)
SELECT 'Hostel Administration', 'Handles hostel complaints.'
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM departments
    WHERE department_name = 'Hostel Administration'
);

INSERT INTO departments (department_name, description)
SELECT 'Transport Department', 'Handles transport complaints.'
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM departments
    WHERE department_name = 'Transport Department'
);

INSERT INTO departments (department_name, description)
SELECT 'General Administration', 'Handles complaints without another category.'
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM departments
    WHERE department_name = 'General Administration'
);

INSERT INTO complaint_categories (category_name, default_department_id)
SELECT 'Wi-Fi / Internet', department_id
FROM departments
WHERE department_name = 'IT Department'
  AND NOT EXISTS (
      SELECT 1 FROM complaint_categories
      WHERE category_name = 'Wi-Fi / Internet'
  );

INSERT INTO complaint_categories (category_name, default_department_id)
SELECT 'Food / Canteen', department_id
FROM departments
WHERE department_name = 'Canteen Administration'
  AND NOT EXISTS (
      SELECT 1 FROM complaint_categories
      WHERE category_name = 'Food / Canteen'
  );

INSERT INTO complaint_categories (category_name, default_department_id)
SELECT 'Faculty / Teaching', department_id
FROM departments
WHERE department_name = 'Academic Administration'
  AND NOT EXISTS (
      SELECT 1 FROM complaint_categories
      WHERE category_name = 'Faculty / Teaching'
  );

INSERT INTO complaint_categories (category_name, default_department_id)
SELECT 'Classroom / Equipment', department_id
FROM departments
WHERE department_name = 'Maintenance Department'
  AND NOT EXISTS (
      SELECT 1 FROM complaint_categories
      WHERE category_name = 'Classroom / Equipment'
  );

INSERT INTO complaint_categories (category_name, default_department_id)
SELECT 'Cleanliness / Sanitation', department_id
FROM departments
WHERE department_name = 'Housekeeping'
  AND NOT EXISTS (
      SELECT 1 FROM complaint_categories
      WHERE category_name = 'Cleanliness / Sanitation'
  );

INSERT INTO complaint_categories (category_name, default_department_id)
SELECT 'Hostel', department_id
FROM departments
WHERE department_name = 'Hostel Administration'
  AND NOT EXISTS (
      SELECT 1 FROM complaint_categories
      WHERE category_name = 'Hostel'
  );

INSERT INTO complaint_categories (category_name, default_department_id)
SELECT 'Transport', department_id
FROM departments
WHERE department_name = 'Transport Department'
  AND NOT EXISTS (
      SELECT 1 FROM complaint_categories
      WHERE category_name = 'Transport'
  );

INSERT INTO complaint_categories (category_name, default_department_id)
SELECT 'Other', department_id
FROM departments
WHERE department_name = 'General Administration'
  AND NOT EXISTS (
      SELECT 1 FROM complaint_categories
      WHERE category_name = 'Other'
  );

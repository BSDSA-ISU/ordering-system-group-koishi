INSERT INTO staff
    (first_name, last_name, role, hire_date,
     username, password_hash, is_active)
VALUES
    ('Ali', 'Houraisan', 'Owner', CURRENT_DATE,
     'ali', 'scrypt:32768:8:1$lXQnV1WhcYPgFu4m$896e2423775cd94e602930acba93a92ae3fc58ab6b9d639e163f9defa5b84c210411e9a6b643ee16ca4a6309f87d74efc481891d19aad626c0204bb3eb76fa0b', 1);

SELECT staff_id, first_name, last_name, role, username, is_active
FROM staff;
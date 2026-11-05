-- 1. Все вопросы с названиями разделов и именами авторов.
SELECT q.id, q.title, s.name AS section, u.name AS author, q.created_at,
       q.status
FROM questions AS q
JOIN sections AS s ON s.id = q.section_id
JOIN users AS u ON u.id = q.user_id
ORDER BY q.created_at DESC, q.id DESC;

-- без связных таблиц
--SELECT q.id, q.title, q.created_at
--FROM questions AS q
--ORDER BY q.created_at DESC;

-- 2. Вопросы в выбранном статусе.
SELECT id, title, created_at
FROM questions
--'closed' / 'open'
WHERE status = ?
ORDER BY created_at DESC;

-- 3. Вопросы, созданные в выбранную дату.
SELECT id, title, status
FROM questions
--'2026-10-09' / '2026-10-03'
WHERE created_at = '2026-10-03'
ORDER BY id;

-- 4. Вопросы выбранного раздела.
SELECT q.id, q.title, q.created_at, q.status
FROM questions AS q
JOIN sections AS s ON s.id = q.section_id
WHERE s.name = ?
ORDER BY q.created_at DESC;

-- 5. Ответы на вопрос с именами авторов.
SELECT a.id, a.text, a.created_at, u.name AS author
FROM answers AS a
JOIN users AS u ON u.id = a.user_id
WHERE a.question_id = ?
ORDER BY a.id;

-- 6. Вопросы без ответов.
SELECT q.id, q.title
FROM questions AS q
LEFT JOIN answers AS a ON a.question_id = q.id
WHERE a.id IS NULL
ORDER BY q.created_at DESC;

-- 7. Общее количество вопросов.
SELECT COUNT(*) AS questions_count
FROM questions;

-- 8. Общее количество ответов.
SELECT COUNT(*) AS answers_count
FROM answers;

-- 9. Количество вопросов в каждом разделе.
SELECT s.name, COUNT(q.id) AS questions_count
FROM sections AS s
LEFT JOIN questions AS q ON q.section_id = s.id
GROUP BY s.id, s.name
ORDER BY s.name;

-- 10. Количество ответов на каждый вопрос.
SELECT q.id, q.title, COUNT(a.id) AS answers_count
FROM questions AS q
LEFT JOIN answers AS a ON a.question_id = q.id
GROUP BY q.id, q.title
ORDER BY answers_count DESC, q.id;

-- 11. Разделы, в которых вопросов не меньше заданного количества.
SELECT s.name, COUNT(q.id) AS questions_count
FROM sections AS s
LEFT JOIN questions AS q ON q.section_id = s.id
GROUP BY s.id, s.name
HAVING COUNT(q.id) >= ?
ORDER BY questions_count DESC;

-- 12. Количество вопросов каждого статуса.
SELECT status, COUNT(*) AS questions_count
FROM questions
GROUP BY status
ORDER BY status;

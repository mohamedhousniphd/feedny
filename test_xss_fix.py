import re
import html

# Test case 1: student_page logic
def test_student_page():
    html_content = "<div>{{ device_id }}</div> <div>{{ can_submit }}</div> <div>{{ question }}</div> <div>Feedny</div>"
    device_id = "<script>alert(1)</script>"
    can_submit = True
    question = "How was <it>?"
    teacher = {"name": "Test <Teacher>"}

    html_content = re.sub(r'\{\{\s*device_id\s*\}\}', html.escape(device_id), html_content)
    html_content = re.sub(r'\{\{\s*can_submit\s*\}\}', str(can_submit).lower(), html_content)
    html_content = re.sub(r'\{\{\s*question\s*\}\}', html.escape(question), html_content)
    html_content = html_content.replace('Feedny', f"Afeedny - {html.escape(teacher['name'])}")

    assert "<script>" not in html_content
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_content
    assert "&lt;it&gt;" in html_content
    assert "Afeedny - Test &lt;Teacher&gt;" in html_content
    print("test_student_page passed")

# Test case 2: teacher_dashboard logic
def test_teacher_dashboard():
    html_content = "<div>{{name}}</div> <div>{{unique_code}}</div> <div>{{credits}}</div>"
    teacher = {
        'name': '<TestName>',
        'unique_code': '<CODE>',
        'credits': 100,
        'is_admin': False
    }

    html_content = html_content.replace('{{name}}', html.escape(teacher['name']))
    html_content = html_content.replace('{{unique_code}}', html.escape(teacher['unique_code']))

    credits_display = '∞' if teacher['is_admin'] else str(teacher['credits'])
    html_content = html_content.replace('{{credits}}', html.escape(credits_display))

    assert "<TestName>" not in html_content
    assert "&lt;TestName&gt;" in html_content
    assert "&lt;CODE&gt;" in html_content
    assert "100" in html_content
    print("test_teacher_dashboard passed")

# Test case 3: reset_password_page logic
def test_reset_password_page():
    html_content = "<script>var token = '{{token}}';</script>"
    token = "'; alert(1); //"

    html_content = html_content.replace('{{token}}', html.escape(token))

    assert "'; alert(1); //" not in html_content
    assert "&#x27;; alert(1); //" in html_content
    print("test_reset_password_page passed")

if __name__ == '__main__':
    test_student_page()
    test_teacher_dashboard()
    test_reset_password_page()

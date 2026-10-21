from flask import Flask, jsonify, request

app = Flask(__name__)

students = [
    {
        "id": 1,
        "name": "Rhea Kapoor",
        "course": "Python",
        "score": 82
    },
    {
        "id": 2,
        "name": "Zain Malik",
        "course": "SQL",
        "score": 76
    },
    {
        "id": 3,
        "name": "Devika Rao",
        "course": "Cloud",
        "score": 91
    }
]

@app.route("/students")
def get_students():


    return jsonify(students)


@app.route("/students/<int:student_id>")
def get_student(student_id):


    for student in students:
        if student["id"] == student_id:
            return jsonify(student)

    return jsonify({"message": "Student not found"}), 404


@app.route("/students", methods=["POST"])
def add_student():
    new_student = request.get_json()

    students.append(new_student)

    return jsonify({
        "message": "Student added successfully",
        "student": new_student
    }), 201

@app.route("/students/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    for student in students:
        if student["id"] == student_id:
            new_student = request.get_json()

            student["name"] = new_student["name"]
            student["course"] = new_student["course"]
            student["score"] = new_student["score"]

            return jsonify({
                "message": "Student updated successfully",
                "student": student
            }), 200

    return jsonify({"message": "Student not found"}), 404

@app.route("/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    for student in students:
        if student["id"] == student_id:
            students.remove(student)
            return jsonify({"message": "Student deleted successfully"}), 200

    return jsonify({"message": "Student not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)

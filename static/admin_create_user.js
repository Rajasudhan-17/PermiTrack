document.addEventListener("DOMContentLoaded", function () {
  const role = document.getElementById("role");
  const sharedDepartment = document.getElementById("shared_department_id");
  const sharedClass = document.getElementById("shared_class_group_id");
  const studentDepartment = document.getElementById("student_department_id");
  const studentYear = document.getElementById("student_year");
  const studentSection = document.getElementById("student_section");
  const facultyDepartment = document.getElementById("faculty_department_id");
  const facultyYear = document.getElementById("faculty_year");
  const facultySection = document.getElementById("faculty_section");
  const hodDepartment = document.getElementById("hod_department_id");
  const classGroupDataNode = document.getElementById("class-group-data");
  const classGroupData = classGroupDataNode ? JSON.parse(classGroupDataNode.textContent) : [];

  const panels = {
    student: document.getElementById("student-fields"),
    faculty: document.getElementById("faculty-fields"),
    hod: document.getElementById("hod-fields"),
    admin: document.getElementById("admin-fields"),
  };

  function togglePanel(activeRole) {
    Object.entries(panels).forEach(([panelRole, panel]) => {
      panel.classList.toggle("d-none", panelRole !== activeRole);
    });
  }

  function setOptions(selectElement, values, placeholder) {
    const currentValue = selectElement.value;
    selectElement.innerHTML = "";

    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = placeholder;
    selectElement.appendChild(defaultOption);

    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      selectElement.appendChild(option);
    });

    if (values.includes(currentValue)) {
      selectElement.value = currentValue;
    }
  }

  function getUniqueValues(items, selector) {
    return [...new Set(items.map(selector))].sort((left, right) => {
      const leftNumber = Number(left);
      const rightNumber = Number(right);
      if (!Number.isNaN(leftNumber) && !Number.isNaN(rightNumber)) {
        return leftNumber - rightNumber;
      }
      return String(left).localeCompare(String(right));
    });
  }

  function findClassGroup(departmentId, year, section) {
    return classGroupData.find(
      (classGroup) =>
        classGroup.departmentId === departmentId &&
        classGroup.year === year &&
        classGroup.section === section
    );
  }

  function populateYears(departmentSelect, yearSelect) {
    const departmentId = departmentSelect.value;
    const matchingClasses = classGroupData.filter((classGroup) => classGroup.departmentId === departmentId);
    const yearOptions = departmentId ? getUniqueValues(matchingClasses, (classGroup) => classGroup.year) : [];
    setOptions(yearSelect, yearOptions, "Select year");
  }

  function populateSections(departmentSelect, yearSelect, sectionSelect) {
    const departmentId = departmentSelect.value;
    const year = yearSelect.value;
    const matchingClasses = classGroupData.filter(
      (classGroup) => classGroup.departmentId === departmentId && classGroup.year === year
    );
    const sectionOptions =
      departmentId && year ? getUniqueValues(matchingClasses, (classGroup) => classGroup.section) : [];
    setOptions(sectionSelect, sectionOptions, "Select section");
  }

  function syncRoleState() {
    const selectedRole = role.value;
    togglePanel(selectedRole);

    sharedDepartment.value = "";
    sharedClass.value = "";

    studentDepartment.required = selectedRole === "student";
    studentYear.required = selectedRole === "student";
    studentSection.required = selectedRole === "student";
    facultyDepartment.required = selectedRole === "faculty";
    facultyYear.required = selectedRole === "faculty";
    facultySection.required = selectedRole === "faculty";
    hodDepartment.required = selectedRole === "hod";

    if (selectedRole === "student") {
      sharedDepartment.value = studentDepartment.value;
      const studentClassGroup = findClassGroup(studentDepartment.value, studentYear.value, studentSection.value);
      sharedClass.value = studentClassGroup ? studentClassGroup.id : "";
    } else if (selectedRole === "faculty") {
      sharedDepartment.value = facultyDepartment.value;
      const facultyClassGroup = findClassGroup(facultyDepartment.value, facultyYear.value, facultySection.value);
      sharedClass.value = facultyClassGroup ? facultyClassGroup.id : "";
    } else if (selectedRole === "hod") {
      sharedDepartment.value = hodDepartment.value;
    }
  }

  studentDepartment.addEventListener("change", function () {
    populateYears(studentDepartment, studentYear);
    setOptions(studentSection, [], "Select section");
    syncRoleState();
  });

  facultyDepartment.addEventListener("change", function () {
    populateYears(facultyDepartment, facultyYear);
    setOptions(facultySection, [], "Select section");
    syncRoleState();
  });

  studentYear.addEventListener("change", function () {
    populateSections(studentDepartment, studentYear, studentSection);
    syncRoleState();
  });

  facultyYear.addEventListener("change", function () {
    populateSections(facultyDepartment, facultyYear, facultySection);
    syncRoleState();
  });

  studentSection.addEventListener("change", syncRoleState);
  facultySection.addEventListener("change", syncRoleState);
  hodDepartment.addEventListener("change", syncRoleState);
  role.addEventListener("change", syncRoleState);

  populateYears(studentDepartment, studentYear);
  populateSections(studentDepartment, studentYear, studentSection);
  populateYears(facultyDepartment, facultyYear);
  populateSections(facultyDepartment, facultyYear, facultySection);
  syncRoleState();
});

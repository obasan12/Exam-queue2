document.addEventListener("DOMContentLoaded", () => {
  // Toast notification system
  window.showToast = (title, message, type = "success") => {
    const toastContainer = document.getElementById("toast-container")
    if (!toastContainer) {
      const container = document.createElement("div")
      container.id = "toast-container"
      container.className = "toast-container"
      document.body.appendChild(container)
    }

    const toast = document.createElement("div")
    toast.className = `toast toast-${type}`
    toast.innerHTML = `
            <div>
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close">&times;</button>
        `

    document.getElementById("toast-container").appendChild(toast)

    // Auto remove after 5 seconds
    setTimeout(() => {
      toast.style.animation = "slideOut 0.3s ease-out forwards"
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast)
        }
      }, 300)
    }, 5000)

    // Close button
    toast.querySelector(".toast-close").addEventListener("click", () => {
      toast.style.animation = "slideOut 0.3s ease-out forwards"
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast)
        }
      }, 300)
    })
  }

  // Modal functionality
  const modals = document.querySelectorAll(".modal")
  const modalTriggers = document.querySelectorAll("[data-modal-target]")
  const modalCloseButtons = document.querySelectorAll(".modal .close, .modal-close")

  modalTriggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const modalId = trigger.dataset.modalTarget
      const modal = document.getElementById(modalId)
      if (modal) {
        modal.style.display = "block"
      }
    })
  })

  modalCloseButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const modal = button.closest(".modal")
      if (modal) {
        modal.style.display = "none"
      }
    })
  })

  window.addEventListener("click", (e) => {
    modals.forEach((modal) => {
      if (e.target === modal) {
        modal.style.display = "none"
      }
    })
  })

  // FAQ toggle
  const faqItems = document.querySelectorAll(".faq-item")

  faqItems.forEach((item) => {
    const question = item.querySelector(".faq-question")
    const answer = item.querySelector(".faq-answer")

    if (question && answer) {
      question.addEventListener("click", () => {
        // Close all other answers
        faqItems.forEach((otherItem) => {
          if (otherItem !== item) {
            otherItem.classList.remove("active")
          }
        })

        // Toggle current answer
        item.classList.toggle("active")
      })
    }
  })

  // Registration steps
  const registrationSteps = document.querySelectorAll(".step[data-step]")
  const stepContents = document.querySelectorAll(".step-content")

  function goToStep(step) {
    // Update steps
    registrationSteps.forEach((el) => {
      const stepNum = Number.parseInt(el.dataset.step)
      if (stepNum === step) {
        el.classList.add("active")
        el.classList.remove("completed")
      } else if (stepNum < step) {
        el.classList.add("completed")
        el.classList.remove("active")
      } else {
        el.classList.remove("active", "completed")
      }
    })

    // Show correct content
    stepContents.forEach((el) => {
      el.classList.remove("active")
    })

    const activeContent = document.getElementById(`step${step}Content`)
    if (activeContent) {
      activeContent.classList.add("active")
    }
  }

  // Expose goToStep to window for use in other scripts
  window.goToStep = goToStep

  // Admin dashboard functionality
  const applyFiltersBtn = document.getElementById("applyFilters")
  if (applyFiltersBtn) {
    applyFiltersBtn.addEventListener("click", () => {
      const center = document.getElementById("centerFilter").value
      const timeSlot = document.getElementById("timeFilter").value
      const level = document.getElementById("levelFilter").value

      fetchStudents(center, timeSlot, level)
    })
  }

  // Function to fetch students with filters
  function fetchStudents(center = "all", timeSlot = "all", level = "all") {
    fetch(`/api/students?center=${center}&timeSlot=${timeSlot}&level=${level}`)
      .then((response) => response.json())
      .then((students) => {
        const tableBody = document.getElementById("studentsTableBody")
        if (!tableBody) return

        tableBody.innerHTML = ""

        if (students.length === 0) {
          const row = document.createElement("tr")
          row.innerHTML = `<td colspan="9" class="text-center">No students found matching the criteria.</td>`
          tableBody.appendChild(row)
          return
        }

        students.forEach((student) => {
          const row = document.createElement("tr")

          let statusBadge = ""
          if (student.status === "Present") {
            statusBadge = '<span class="badge badge-success">Present</span>'
          } else if (student.status === "Absent") {
            statusBadge = '<span class="badge badge-danger">Absent</span>'
          } else {
            statusBadge = '<span class="badge badge-warning">Scheduled</span>'
          }

          row.innerHTML = `
                        <td>${student.matricNumber}</td>
                        <td>${student.fullName}</td>
                        <td>${student.level}</td>
                        <td>${student.department || ""}</td>
                        <td>${student.examTime}</td>
                        <td>${student.examCenter}</td>
                        <td>${student.tokenId}</td>
                        <td>${statusBadge}</td>
                        <td>
                            <button class="btn btn-sm btn-success mark-present" data-matric="${student.matricNumber}">Present</button>
                            <button class="btn btn-sm btn-danger mark-absent" data-matric="${student.matricNumber}">Absent</button>
                        </td>
                    `

          tableBody.appendChild(row)
        })

        // Add event listeners for mark present/absent buttons
        document.querySelectorAll(".mark-present").forEach((button) => {
          button.addEventListener("click", function () {
            updateStatus(this.dataset.matric, "Present")
          })
        })

        document.querySelectorAll(".mark-absent").forEach((button) => {
          button.addEventListener("click", function () {
            updateStatus(this.dataset.matric, "Absent")
          })
        })
      })
      .catch((error) => {
        console.error("Error fetching students:", error)
        window.showToast("Error", "Failed to fetch students. Please try again.", "error")
      })
  }

  // Function to update student status
  function updateStatus(matricNumber, status) {
    fetch("/api/update-status", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        matricNumber: matricNumber,
        status: status,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.error) {
          window.showToast("Error", data.error, "error")
        } else {
          window.showToast("Success", `Student marked as ${status}`, "success")

          // Refresh the student list
          const center = document.getElementById("centerFilter")?.value || "all"
          const timeSlot = document.getElementById("timeFilter")?.value || "all"
          const level = document.getElementById("levelFilter")?.value || "all"

          fetchStudents(center, timeSlot, level)
        }
      })
      .catch((error) => {
        console.error("Error updating status:", error)
        window.showToast("Error", "Failed to update student status. Please try again.", "error")
      })
  }

  // Initialize dashboard if on dashboard page
  const studentsTable = document.getElementById("studentsTable")
  if (studentsTable) {
    fetchStudents()
  }

  // File upload preview
  const csvFileInput = document.getElementById("csvFile")
  if (csvFileInput) {
    csvFileInput.addEventListener("change", (e) => {
      const file = e.target.files[0]
      if (file) {
        const reader = new FileReader()
        reader.onload = (e) => {
          const contents = e.target.result
          const lines = contents.split("\n")

          const csvPreview = document.getElementById("csvPreview")
          const csvPreviewBody = document.getElementById("csvPreviewBody")

          if (csvPreview && csvPreviewBody) {
            // Clear previous preview
            csvPreviewBody.innerHTML = ""

            // Skip header row and process data rows
            for (let i = 1; i < Math.min(lines.length, 6); i++) {
              if (lines[i].trim() === "") continue

              const cells = lines[i].split(",")
              if (cells.length >= 3) {
                const row = document.createElement("tr")

                // Matric Number
                const matricCell = document.createElement("td")
                matricCell.textContent = cells[0].trim()
                row.appendChild(matricCell)

                // Full Name
                const nameCell = document.createElement("td")
                nameCell.textContent = cells[1].trim()
                row.appendChild(nameCell)

                // Level
                const levelCell = document.createElement("td")
                levelCell.textContent = cells[2].trim()
                row.appendChild(levelCell)

                // Department (if available)
                const deptCell = document.createElement("td")
                deptCell.textContent = cells.length > 3 ? cells[3].trim() : ""
                row.appendChild(deptCell)

                csvPreviewBody.appendChild(row)
              }
            }

            csvPreview.style.display = "block"
          }
        }
        reader.readAsText(file)
      }
    })
  }

  // Upload form submission
  const uploadForm = document.getElementById("uploadForm")
  if (uploadForm) {
    uploadForm.addEventListener("submit", (e) => {
      e.preventDefault()

      const formData = new FormData(uploadForm)

      fetch("/api/upload-students", {
        method: "POST",
        body: formData,
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.error) {
            window.showToast("Error", data.error, "error")
          } else {
            window.showToast(
              "Success",
              `${data.message}. Added: ${data.success}, Duplicates: ${data.duplicates}, Errors: ${data.errors}`,
              "success",
            )

            // Reset form
            uploadForm.reset()

            // Hide preview
            const csvPreview = document.getElementById("csvPreview")
            if (csvPreview) {
              csvPreview.style.display = "none"
            }

            // Close modal
            const modal = uploadForm.closest(".modal")
            if (modal) {
              modal.style.display = "none"
            }

            // Refresh stats and student list
            fetchStats()
            fetchStudents()
          }
        })
        .catch((error) => {
          console.error("Error uploading students:", error)
          window.showToast("Error", "Failed to upload students. Please try again.", "error")
        })
    })
  }

  // Function to fetch dashboard stats
  function fetchStats() {
    const totalStudents = document.getElementById("totalStudents")
    const totalScheduled = document.getElementById("totalScheduled")
    const level100 = document.getElementById("level100")
    const level200 = document.getElementById("level200")

    if (totalStudents || totalScheduled || level100 || level200) {
      fetch("/api/stats")
        .then((response) => response.json())
        .then((stats) => {
          if (totalStudents) totalStudents.textContent = stats.totalStudents
          if (totalScheduled) totalScheduled.textContent = stats.totalScheduled
          if (level100) level100.textContent = stats.levelDistribution["100L"]
          if (level200) level200.textContent = stats.levelDistribution["200L"]
        })
        .catch((error) => {
          console.error("Error fetching stats:", error)
        })
    }
  }

  // Initialize stats if on dashboard page
  if (document.getElementById("totalStudents")) {
    fetchStats()
  }

  // Set current year in footer
  const currentYearElements = document.querySelectorAll(".current-year")
  currentYearElements.forEach((el) => {
    el.textContent = new Date().getFullYear()
  })
})

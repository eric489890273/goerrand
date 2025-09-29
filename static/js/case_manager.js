// 對照表
const STATUS_MAP = {
    pending: "待處理",
    accepted: "已接取",
    in_progress: "進行中",
    delivered: "已送達",
    done: "已完成"
};

// case_manager.js
export async function fetchCases(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error("抓取案件失敗");
    return await res.json();
}

// 生成卡片
export function createCaseCard(caseData, type = "pending", container, openUpdateModal) {
    const div = document.createElement("div");
    div.className = "col-12";
    div.dataset.caseId = caseData.id; // ✅ 保留
    // 判斷是否完成
    const isDone = caseData.status === "done";
    div.innerHTML = `
        <div class="card p-3">
            <div>
            <strong>${caseData.document_name || "無文件名稱"}</strong><br>
            交付對象: ${caseData.delivery_target || "無"}<br>
            客戶給予地點: ${caseData.given_location || "無"}<br>
            交付時間: ${caseData.given_to_staff_time || "無"}<br>
            狀態: <span class="status-text">${STATUS_MAP[caseData.status] || caseData.status}</span><br>
            備註: ${caseData.note || "無"}   <!-- ✅ 新增 -->
            </div>
            <button class="btn ${type === "pending" ? "btn-success" : "btn-warning"} btn-sm mt-2">
            ${type === "pending" ? "接取" : "更新進度"}
            </button>
        </div>
        `;

    const btn = div.querySelector("button");

    if (type === "pending") {
        btn.className = "btn btn-success btn-sm mt-2";
        btn.addEventListener("click", () => takeCase(caseData.id, div, container, openUpdateModal));
    } else {
        // 判斷案件是否完成
        if (caseData.status === "done") {
            btn.textContent = "已完成";
            btn.className = "btn btn-secondary btn-sm mt-2";
            btn.disabled = true;
        } else {
            btn.className = "btn btn-warning btn-sm mt-2";
            btn.addEventListener("click", () => openUpdateModal(caseData.id, div));
        }
    }

    container.appendChild(div);
}


// 接取案件
export async function takeCase(caseId, divElement, takenContainer, openUpdateModal) {
    try {
        const res = await fetch(`/update_taken_case/${caseId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: "accepted", note: "員工已接取" })
        });
        const data = await res.json();
        if (data.message) {
            divElement.querySelector(".status-text").textContent = STATUS_MAP["accepted"];


            const btn = divElement.querySelector("button");
            const newBtn = btn.cloneNode(true);

            // 判斷是否完成
            const isDone = "accepted" === "done"; // 接取後通常不是完成，這裡保留邏輯
            newBtn.className = "btn btn-warning btn-sm mt-2";

            if (isDone) {
                newBtn.textContent = "已完成";
                newBtn.disabled = true;
            } else {
                newBtn.textContent = "更新進度";
                newBtn.addEventListener("click", () => openUpdateModal(caseId, divElement));
            }

            btn.replaceWith(newBtn);
            takenContainer.appendChild(divElement);
        } else {
            alert("接取失敗：" + (data.error || ""));
        }
    } catch (err) {
        alert("接取案件發生錯誤：" + err.message);
    }
}

// 打開更新進度 Modal
export function setupUpdateModal(modalId, formId) {
    const modalEl = document.getElementById(modalId);
    const form = document.getElementById(formId);
    const modal = new bootstrap.Modal(modalEl);

// 單一 submit handler
form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const caseId = document.getElementById("updateCaseId").value;
    const status = document.getElementById("statusSelect").value;
    const note = document.getElementById("noteInput").value;
    const location = document.getElementById("locationInput").value;

    const divElement = document.querySelector(`[data-case-id="${caseId}"]`);

    try {
        const res = await fetch(`/update_taken_case/${caseId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status, note, location })
        });
        const data = await res.json();

        if (data.message && divElement) {
            // 更新狀態文字
            const statusSpan = divElement.querySelector(".status-text");
            statusSpan.textContent = STATUS_MAP[status] || status;

            // 更新按鈕
            const oldBtn = divElement.querySelector("button");
            const newBtn = oldBtn.cloneNode(true);

            if (status === "done") {
                // 完成案件 → 禁用按鈕、文字變灰
                newBtn.disabled = true;
                newBtn.textContent = "已完成";
                newBtn.className = "btn btn-secondary btn-sm mt-2";
            } else {
                // 尚未完成 → 按鈕可用
                newBtn.disabled = false;
                newBtn.textContent = "更新進度";
                newBtn.className = "btn btn-warning btn-sm mt-2";
                newBtn.addEventListener("click", () => openUpdateModal(caseId, divElement));
            }

            oldBtn.replaceWith(newBtn);

            modal.hide();
        } else {
            alert("更新失敗：" + (data.error || ""));
        }
    } catch (err) {
        alert("更新案件發生錯誤：" + err.message);
    }
});


    const openUpdateModal = (caseId, divElement) => {
    const currentStatus = divElement.querySelector(".status-text").textContent;

    if (currentStatus === "done") {
        alert("此案件已完成，不可再修改進度");
        return; // 不打開 Modal
    }

    document.getElementById("updateCaseId").value = caseId;
    document.getElementById("statusSelect").value = currentStatus;
    document.getElementById("noteInput").value = "";
    document.getElementById("locationInput").value = "";

    divElement.dataset.caseId = caseId;
    modal.show();
};

    return openUpdateModal;
}

// 更新案件表格
export function populateTable(tableBodyId, cases) {
    const tbody = document.getElementById(tableBodyId);
    tbody.innerHTML = "";
    cases.forEach(c => {
        const updates = (c.updates || []).map(u =>`${u.time} ${STATUS_MAP[u.status] || u.status} (${u.note || ''})`)
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${c.id}</td>
            <td>${c.document_name || ""}</td>
            <td>${c.delivery_target || ""}</td>
            <td>${c.given_location || ""}</td>
            <td>${c.given_to_staff_time || ""}</td>
            <td>${STATUS_MAP[c.status] || c.status}</td>
            <td>${c.note || ""}</td>   <!-- ✅ 新增 -->
            <td>${updates}</td>
        `;
        tbody.appendChild(tr);
    });
}

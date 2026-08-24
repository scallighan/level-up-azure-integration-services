const apiForm = document.querySelector("#api-form");
const itemForm = document.querySelector("#item-form");
const connectionModeInput = document.querySelector("#connection-mode");
const apiBaseInput = document.querySelector("#api-base");
const idInput = document.querySelector("#item-id");
const nameInput = document.querySelector("#item-name");
const statusInput = document.querySelector("#item-status");
const itemsBody = document.querySelector("#items");
const message = document.querySelector("#message");

connectionModeInput.value =
  localStorage.getItem("workshopConnectionMode") || "direct";
localStorage.removeItem("workshopApiBase");

function endpoint() {
  return apiBaseInput.value.trim().replace(/\/$/, "");
}

function updateConnectionMode() {
  const gatewayMode = connectionModeInput.value === "gateway";
  apiBaseInput.placeholder = gatewayMode
    ? "https://example.azure-api.net/workshop"
    : "Paste the temporary Logic App callback URL";
  apiBaseInput.value = gatewayMode
    ? localStorage.getItem("workshopGatewayBase") || ""
    : "";
}

function showMessage(text, isError = false) {
  message.textContent = text;
  message.className = isError ? "error" : "";
}

async function request(path, options = {}) {
  if (!endpoint()) {
    throw new Error("Enter the endpoint first.");
  }

  const method = options.method || "GET";
  const match = path.match(/^\/items(?:\/([^/]+))?$/);
  const operationIds = {
    "GET:false": "listItems",
    "POST:false": "createItem",
    "GET:true": "getItem",
    "PUT:true": "updateItem",
    "DELETE:true": "deleteItem",
  };
  const itemId = match?.[1] ? decodeURIComponent(match[1]) : null;
  const operationId = operationIds[`${method}:${Boolean(itemId)}`];

  const requestUrl =
    connectionModeInput.value === "gateway" ? `${endpoint()}${path}` : endpoint();
  const requestOptions =
    connectionModeInput.value === "gateway"
      ? options
      : {
          method: "POST",
          body: JSON.stringify({
            operationId,
            itemId,
            body: options.body ? JSON.parse(options.body) : null,
            correlationId: crypto.randomUUID(),
          }),
        };

  const response = await fetch(requestUrl, {
    ...requestOptions,
    headers: {
      "Content-Type": "application/json",
      ...requestOptions.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status}: ${body || response.statusText}`);
  }

  return response.status === 204 ? null : response.json();
}

function resetForm() {
  idInput.value = "";
  nameInput.value = "";
  statusInput.value = "new";
  nameInput.focus();
}

function beginEdit(item) {
  idInput.value = item.id;
  nameInput.value = item.name;
  statusInput.value = item.status;
  nameInput.focus();
}

async function deleteItem(id) {
  try {
    await request(`/items/${encodeURIComponent(id)}`, { method: "DELETE" });
    showMessage("Item deleted.");
    await loadItems();
  } catch (error) {
    showMessage(error.message, true);
  }
}

function renderItems(items) {
  itemsBody.replaceChildren();

  for (const item of items) {
    const row = document.createElement("tr");
    const name = document.createElement("td");
    const status = document.createElement("td");
    const actions = document.createElement("td");
    const edit = document.createElement("button");
    const remove = document.createElement("button");

    name.textContent = item.name;
    status.textContent = item.status;
    edit.textContent = "Edit";
    edit.className = "secondary";
    edit.addEventListener("click", () => beginEdit(item));
    remove.textContent = "Delete";
    remove.className = "danger";
    remove.addEventListener("click", () => deleteItem(item.id));
    actions.append(edit, remove);
    row.append(name, status, actions);
    itemsBody.append(row);
  }
}

async function loadItems() {
  try {
    renderItems(await request("/items"));
    showMessage("Items loaded.");
  } catch (error) {
    showMessage(error.message, true);
  }
}

apiForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  localStorage.setItem("workshopConnectionMode", connectionModeInput.value);
  if (connectionModeInput.value === "gateway") {
    localStorage.setItem("workshopGatewayBase", endpoint());
  }
  await loadItems();
});

itemForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = idInput.value;
  const body = { name: nameInput.value, status: statusInput.value };

  try {
    if (id) {
      await request(`/items/${encodeURIComponent(id)}`, {
        method: "PUT",
        body: JSON.stringify(body),
      });
    } else {
      await request("/items", {
        method: "POST",
        body: JSON.stringify({ id: crypto.randomUUID(), ...body }),
      });
    }
    resetForm();
    showMessage("Item saved.");
    await loadItems();
  } catch (error) {
    showMessage(error.message, true);
  }
});

document.querySelector("#cancel-edit").addEventListener("click", resetForm);
document.querySelector("#refresh").addEventListener("click", loadItems);
connectionModeInput.addEventListener("change", updateConnectionMode);
updateConnectionMode();

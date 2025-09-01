<script lang="ts">
    let username = $state("");
    let password = $state("");
    let messageRows: MessageRow[] = $state([]);
    let loading = $state(false);
    let error = $state("");
    let sessionToken = $state("");
    let session = $state("");
    let didLogin = $state(false);
    let sessionLoginError = $state(false);
    let pollNames: string[] = $state([]);
    let selectedPoll = $state("");
    let currentPage = $state("home");
    let stats = $state({});

    import Stats from "./lib/Stats.svelte"

    type MessageRow = {
        name: string;
        number: string;
        message?: string;
        is_read: boolean;
        created_at: string;
        poll_name?: string;
    };

    session =
        document.cookie
            .split("; ")
            .find((row) => row.startsWith("session="))
            ?.split("=")[1] || "";

    async function login(): Promise<void> {
        if (session) {
            const response = await fetch(`/wa_message_stats`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ session }),
            });

            if (!response.ok) {
                sessionLoginError = true;
                throw new Error("Login failed");
            }

            const data = await response.json();
            messageRows = data.data || [];
            didLogin = true;
        }
    }

    $effect(() => {
        login();
    });

    async function handleSubmit(event: Event) {
        event.preventDefault();
        loading = true;
        error = "";

        try {
            const response = await fetch(`/wa_message_stats`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ username, password }),
            });

            if (!response.ok) {
                throw new Error("Login failed");
            }

            const data = await response.json();
            messageRows = data.data || [];
            sessionToken = data.session_token;
            didLogin = true;

            if (sessionToken) {
                document.cookie = `session=${sessionToken}; path=/; secure; SameSite=None`;
            }
        } catch (err) {
            error = "Login failed. Please check your credentials.";
        } finally {
            loading = false;
        }
    }

    async function logout() {
        document.cookie =
            "session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; Secure; SameSite=None";
        window.location.href = "/";
    }

    function getPollNames(): void {
        const pollNamesSet = new Set<string>();
        messageRows.forEach((row) => {
            if (row.poll_name) {
                pollNamesSet.add(row.poll_name);
            }
        });
        pollNames = Array.from(pollNamesSet);
    }

    $effect(() => {
        if (messageRows.length > 0) {
            getPollNames();
        }

        if (session) {
          (async () => {
          const statsResponse = await fetch("/wa_message_stats_full", { method: "POST", body: JSON.stringify({ session })});
          if (statsResponse.ok) {
            stats = await statsResponse.json();
            stats = stats.data;
            console.log(stats);
          }
          })();
        }
    });

    let shownMessageRows: MessageRow[] = $derived(
        selectedPoll === ""
            ? messageRows
            : messageRows.filter((row) => row.poll_name === selectedPoll),
    );
</script>

<main>
    <div id="main-content">
        {#if messageRows.length > 0 || (didLogin && messageRows.length === 0)}
            <div class="container">
                <div class="header">
                    <h1>WhatsApp Message Statistics</h1>
                    <div class="logout-div">
                        {#if currentPage === "stats"}
                            <a class="stats" onclick={currentPage = "home"}>home</a>
                        {:else}
                            <a class="stats" onclick={currentPage = "stats"}>stats</a>
                        {/if}

                        {#if messageRows[0]?.poll_name}
                            <select
                                bind:value={selectedPoll}
                                class="poll-select"
                            >
                                <option value="">All Polls</option>
                                {#if pollNames.length > 0}
                                    {#each pollNames as pollName}
                                        <option value={pollName}
                                            >{pollName}</option
                                        >
                                    {/each}
                                {/if}
                            </select>
                        {/if}

                        <button
                            class="logout-button"
                            onclick={() => {
                                logout();
                            }}>Logout</button
                        >
                    </div>
                </div>

                {#if currentPage === "home"}
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Phone Number</th>
                                <th>Message</th>
                                <th>Status</th>
                                <th>Created At</th>
                                {#if messageRows[0]?.poll_name}
                                    <th>Poll Name</th>
                                {/if}
                            </tr>
                        </thead>
                        <tbody>
                            {#each shownMessageRows as row, index}
                                <tr>
                                    <td>{row.name}</td>
                                    <td>{row.number}</td>
                                    <td class="message-cell">
                                        {#if row.message}
                                            <span class="message"
                                                >{row.message}</span
                                            >
                                        {:else}
                                            <span class="no-message"
                                                >No response</span
                                            >
                                        {/if}
                                    </td>
                                    <td>
                                        {#if row.is_read}
                                            <span class="status responded"
                                                >Read</span
                                            >
                                        {:else}
                                            <span class="status no-response"
                                                >Not Read</span
                                            >
                                        {/if}
                                    </td>
                                    <td
                                        >{new Date(
                                            row.created_at.replace(" ", "T") +
                                                "Z",
                                        ).toLocaleString()}</td
                                    >
                                    {#if row?.poll_name}
                                        <td>
                                            <span>{row.poll_name}</span>
                                        </td>
                                    {/if}
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                    {#if messageRows.length === 0 && didLogin}
                        <div class="no-data">No messages found.</div>
                    {/if}
                </div>
                {/if}

                {#if currentPage === "stats"}
                    {#if stats}
                        <Stats {stats} {selectedPoll} />
                    {:else}
                        <div class="no-data">No stats available.</div>
                    {/if}
                {/if}

            </div>

        {:else if session === "" || sessionLoginError === true}
            <div class="login-container">
                <div class="login-form">
                    <h2>Admin Login</h2>
                    <form onsubmit={handleSubmit}>
                        <div class="form-group">
                            <input
                                type="text"
                                placeholder="Username"
                                bind:value={username}
                                disabled={loading}
                                required
                            />
                        </div>
                        <div class="form-group">
                            <input
                                type="password"
                                placeholder="Password"
                                bind:value={password}
                                disabled={loading}
                                required
                            />
                        </div>
                        {#if error}
                            <div class="error">{error}</div>
                        {/if}
                        <button type="submit" disabled={loading}>
                            {loading ? "Logging in..." : "Login"}
                        </button>
                    </form>
                </div>
            </div>
        {/if}
    </div>
</main>

<style>
    :global(body) {
        margin: 0;
        font-family:
            -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background-color: #f5f5f5;
    }

    main {
        height: 100vh;
        width: 100vw;
        display: flex;
        justify-content: center;
        padding: 16px;
        padding-top: 32px;
        padding-left: 0;
    }

    #main-content {
        width: 95%;
        overflow-x: hidden;
    }

    .container {
        width: 100%;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        overflow: hidden;
    }

    .no-data {
        padding: 20px;
        text-align: center;
        color: #6c757d;
        font-size: 16px;
    }

    .header {
        display: flex;
        justify-content: justify-between;
        align-items: center;
        padding: 20px 30px;
        background: #25d366;
        color: white;
    }

    .logout-div {
        display: flex;
        align-items: center;
        margin-left: auto;
    }

    .stats {
        color: black;
        background: white;
        padding: 8px 12px;
        border-radius: 4px;
        border: none;
        font-size: 14px;
        margin-right: 15px;
        cursor: pointer;
    }

    .poll-select {
        background: white;
        padding: 8px 12px;
        border-radius: 4px;
        border: none;
        font-size: 14px;
        margin-right: 15px;
        cursor: pointer;
    }

    .logout-button {
        background: #ff4d4d;
        color: white;
        border: none;
        width: 120px;
        padding: 10px 20px;
        border-radius: 4px;
        cursor: pointer;
        margin-left: auto;
        transition: background-color 0.2s;
    }

    .header h1 {
        margin: 0;
        font-size: 24px;
    }

    .table-container {
        overflow-x: auto;
    }

    table {
        width: 100%;
        border-collapse: collapse;
    }

    thead {
        background: #f8f9fa;
    }

    th,
    td {
        padding: 12px 15px;
        text-align: left;
        border-bottom: 1px solid #e9ecef;
    }

    th {
        font-weight: 600;
        color: #495057;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    td {
        color: #333;
    }

    .message-cell {
        max-width: 300px;
    }

    .message {
        background: #e3f2fd;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 14px;
        display: inline-block;
    }

    .no-message {
        color: #6c757d;
        font-style: italic;
    }

    .status {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
        text-transform: uppercase;
    }

    .status.responded {
        background: #d4edda;
        color: #155724;
    }

    .status.no-response {
        background: #f8d7da;
        color: #721c24;
    }

    tbody tr:hover {
        background: #f8f9fa;
    }

    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
    }

    .login-form {
        background: white;
        padding: 40px;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        width: 100%;
        max-width: 400px;
    }

    .login-form h2 {
        text-align: center;
        margin-bottom: 30px;
        color: #333;
    }

    .form-group {
        margin-bottom: 20px;
    }

    input {
        width: 100%;
        padding: 12px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-size: 16px;
        box-sizing: border-box;
    }

    input:focus {
        outline: none;
        border-color: #25d366;
        box-shadow: 0 0 0 2px rgba(37, 211, 102, 0.2);
    }

    input:disabled {
        background: #f5f5f5;
        cursor: not-allowed;
    }

    button {
        width: 100%;
        background: #25d366;
        color: white;
        border: none;
        padding: 12px;
        border-radius: 4px;
        font-size: 16px;
        cursor: pointer;
        transition: background-color 0.2s;
    }

    button:hover:not(:disabled) {
        background: #128c7e;
    }

    button:disabled {
        background: #ccc;
        cursor: not-allowed;
    }

    .error {
        background: #f8d7da;
        color: #721c24;
        padding: 10px;
        border-radius: 4px;
        margin-bottom: 15px;
        font-size: 14px;
    }

    @media (max-width: 768px) {
        .header {
            flex-direction: column;
            gap: 15px;
            text-align: center;
        }

        .header h1 {
            font-size: 20px;
        }

        table {
            font-size: 14px;
        }

        th,
        td {
            padding: 8px 10px;
        }

        .message-cell {
            max-width: 200px;
        }
    }
</style>

<script lang="ts">
    let username = $state("");
    let password = $state("");
    let messageRows = $state([]);
    let loading = $state(false);
    let error = $state("");
    let sessionToken = $state("");
    let session = $state("");

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
                throw new Error("Login failed");
            }

            const data = await response.json();
            messageRows = data.data || [];
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

            if (sessionToken) {
                document.cookie = `session=${sessionToken}; path=/; secure; SameSite=None`;
            }
        } catch (err) {
            error = "Login failed. Please check your credentials.";
        } finally {
            loading = false;
        }
    }
</script>

<main>
    {#if messageRows.length > 0}
        <div class="container">
            <div class="header">
                <h1>WhatsApp Message Statistics</h1>
            </div>

            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Phone Number</th>
                            <th>Message</th>
                            <th>Status</th>
                            <th>Created At</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each messageRows as row, index}
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
                                        row.created_at.replace(" ", "T") + "Z",
                                    ).toLocaleString()}</td
                                >
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        </div>
    {:else}
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
</main>

<style>
    :global(body) {
        margin: 0;
        font-family:
            -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background-color: #f5f5f5;
    }

    main {
        min-height: 100vh;
        padding: 20px;
    }

    .container {
        width: 100%;
        margin: 8px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        overflow: hidden;
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px 30px;
        background: #25d366;
        color: white;
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

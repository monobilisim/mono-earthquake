<script lang="ts">
  const { stats, selectedPoll } = $props();

  function calculateTotals() {
    const totals = {
      daily_failed: 0,
      daily_successful: 0,
      monthly_failed: 0,
      monthly_successful: 0,
      read_messages: 0,
      total_failed: 0,
      total_messages: 0,
      unread_messages: 0,
      weekly_failed: 0,
      weekly_successful: 0
    };

    Object.values(stats).forEach((pollStats: any) => {
      Object.keys(totals).forEach(key => {
        totals[key] += pollStats[key] || 0;
      });
    });

    return totals;
  }

  function getCurrentStats() {
    if (selectedPoll && stats[selectedPoll]) {
      return stats[selectedPoll];
    }
    return calculateTotals();
  }

  const currentStats = $derived(getCurrentStats());
  const isShowingTotal = $derived(!selectedPoll || !stats[selectedPoll]);

  const dailySuccessRate = $derived(currentStats.daily_successful + currentStats.daily_failed > 0
    ? (currentStats.daily_successful / (currentStats.daily_successful + currentStats.daily_failed)) * 100
    : 0);

  const weeklySuccessRate = $derived(currentStats.weekly_successful + currentStats.weekly_failed > 0
    ? (currentStats.weekly_successful / (currentStats.weekly_successful + currentStats.weekly_failed)) * 100
    : 0);

  const monthlySuccessRate = $derived(currentStats.monthly_successful + currentStats.monthly_failed > 0
    ? (currentStats.monthly_successful / (currentStats.monthly_successful + currentStats.monthly_failed)) * 100
    : 0);

  const readRate = $derived(currentStats.total_messages > 0
    ? (currentStats.read_messages / currentStats.total_messages) * 100
    : 0);

  function getColor(rate: number) {
    if (rate >= 80) return '#22c55e';
    if (rate >= 60) return '#f59e0b';
    return '#ef4444';
  }
</script>

<div class="stats-container">
  <div class="header">
    <h2>Statistics {isShowingTotal ? '' : `- ${selectedPoll}`}</h2>
  </div>

  <div class="metrics-row">
    <div class="metric">
      <div class="value">{currentStats.total_messages}</div>
      <div class="label">Total</div>
    </div>
    <div class="metric">
      <div class="value success">{currentStats.read_messages}</div>
      <div class="label">Read</div>
    </div>
    <div class="metric">
      <div class="value warning">{currentStats.unread_messages}</div>
      <div class="label">Unread</div>
    </div>
    <div class="metric">
      <div class="value error">{currentStats.total_failed}</div>
      <div class="label">Failed</div>
    </div>
  </div>

  <div class="content-grid">
    <div class="chart-section">
      <h3>Success Rates</h3>
      <div class="bars">
        <div class="bar-group">
          <div class="bar">
            <div class="bar-fill" style="height: {dailySuccessRate}%; background-color: {getColor(dailySuccessRate)}"></div>
          </div>
          <div class="bar-info">
            <div class="percentage">{dailySuccessRate.toFixed(0)}%</div>
            <div class="period">Daily</div>
            <div class="counts">{currentStats.daily_successful}/{currentStats.daily_successful + currentStats.daily_failed}</div>
          </div>
        </div>

        <div class="bar-group">
          <div class="bar">
            <div class="bar-fill" style="height: {weeklySuccessRate}%; background-color: {getColor(weeklySuccessRate)}"></div>
          </div>
          <div class="bar-info">
            <div class="percentage">{weeklySuccessRate.toFixed(0)}%</div>
            <div class="period">Weekly</div>
            <div class="counts">{currentStats.weekly_successful}/{currentStats.weekly_successful + currentStats.weekly_failed}</div>
          </div>
        </div>

        <div class="bar-group">
          <div class="bar">
            <div class="bar-fill" style="height: {monthlySuccessRate}%; background-color: {getColor(monthlySuccessRate)}"></div>
          </div>
          <div class="bar-info">
            <div class="percentage">{monthlySuccessRate.toFixed(0)}%</div>
            <div class="period">Monthly</div>
            <div class="counts">{currentStats.monthly_successful}/{currentStats.monthly_successful + currentStats.monthly_failed}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="read-rate-section">
      <h3>Read Rate</h3>
      <div class="progress-circle">
        <svg viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" stroke="#e5e7eb" stroke-width="6" fill="none"/>
          <circle
            cx="50"
            cy="50"
            r="45"
            stroke="{getColor(readRate)}"
            stroke-width="6"
            fill="none"
            stroke-dasharray="{2 * Math.PI * 45}"
            stroke-dashoffset="{2 * Math.PI * 45 * (1 - readRate / 100)}"
            stroke-linecap="round"
            transform="rotate(-90 50 50)"
          />
        </svg>
        <div class="circle-content">
          <div class="circle-percentage">{readRate.toFixed(0)}%</div>
          <div class="circle-label">Read</div>
        </div>
      </div>
    </div>

    <div class="quick-stats">
      <h3>Success Details</h3>
      <div class="stat-row">
        <span>Daily Success</span>
        <span class="success">{currentStats.daily_successful}</span>
      </div>
      <div class="stat-row">
        <span>Weekly Success</span>
        <span class="success">{currentStats.weekly_successful}</span>
      </div>
      <div class="stat-row">
        <span>Monthly Success</span>
        <span class="success">{currentStats.monthly_successful}</span>
      </div>
      <div class="stat-row">
        <span>Total Success</span>
        <span class="success">{currentStats.total_messages - currentStats.total_failed}</span>
      </div>
    </div>

    <div class="quick-stats">
      <h3>Failed details</h3>
      <div class="stat-row">
        <span>Daily Failed</span>
        <span class="error">{currentStats.daily_failed}</span>
      </div>
      <div class="stat-row">
        <span>Weekly Failed</span>
        <span class="error">{currentStats.weekly_failed}</span>
      </div>
      <div class="stat-row">
        <span>Monthly Failed</span>
        <span class="error">{currentStats.monthly_failed}</span>
      </div>
      <div class="stat-row">
        <span>Total Failed</span>
        <span class="error">{currentStats.total_failed}</span>
      </div>
    </div>
  </div>
</div>

<style>
  .stats-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }

  .header {
    margin-bottom: 1rem;
  }

  .header h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: #1f2937;
  }

  .metrics-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .metric {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
  }

  .metric .value {
    font-size: 1.875rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
    color: #374151;
  }

  .metric .value.success { color: #22c55e; }
  .metric .value.warning { color: #f59e0b; }
  .metric .value.error { color: #ef4444; }

  .metric .label {
    font-size: 0.875rem;
    color: #6b7280;
    font-weight: 500;
  }

  .content-grid {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr;
    gap: 1.5rem;
  }

  .chart-section, .read-rate-section, .quick-stats {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1rem;
  }

  .chart-section h3, .read-rate-section h3, .quick-stats h3 {
    margin: 0 0 1rem 0;
    font-size: 1rem;
    font-weight: 600;
    color: #1f2937;
  }

  .bars {
    display: flex;
    justify-content: space-around;
    align-items: end;
    height: 140px;
    gap: 1rem;
  }

  .bar-group {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
  }

  .bar {
    width: 30px;
    height: 100px;
    background: #f3f4f6;
    border-radius: 4px;
    overflow: hidden;
    position: relative;
    margin-bottom: 0.5rem;
  }

  .bar-fill {
    position: absolute;
    bottom: 0;
    width: 100%;
    border-radius: 4px;
    transition: height 0.8s ease;
  }

  .bar-info {
    text-align: center;
  }

  .percentage {
    font-size: 0.875rem;
    font-weight: 600;
    color: #1f2937;
  }

  .period {
    font-size: 0.75rem;
    color: #6b7280;
  }

  .counts {
    font-size: 0.75rem;
    color: #9ca3af;
  }

  .progress-circle {
    position: relative;
    width: 100px;
    height: 100px;
    margin: 0 auto;
  }

  .progress-circle svg {
    width: 100%;
    height: 100%;
  }

  .circle-content {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
  }

  .circle-percentage {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1f2937;
  }

  .circle-label {
    font-size: 0.75rem;
    color: #6b7280;
  }

  .stat-row {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem 0;
    border-bottom: 1px solid #f3f4f6;
    font-size: 0.875rem;
  }

  .stat-row:last-child {
    border-bottom: none;
  }

  .stat-row span:first-child {
    color: #6b7280;
  }

  .stat-row .success {
    color: #22c55e;
    font-weight: 600;
  }

  .stat-row .error {
    color: #ef4444;
    font-weight: 600;
  }

  @media (max-width: 1024px) {
    .content-grid {
      grid-template-columns: 1fr;
    }

    .metrics-row {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 640px) {
    .metrics-row {
      grid-template-columns: 1fr;
    }
  }
</style>

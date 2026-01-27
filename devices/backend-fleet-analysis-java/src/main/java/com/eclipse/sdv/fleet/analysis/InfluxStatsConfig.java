package com.eclipse.sdv.fleet.analysis;

public class InfluxStatsConfig {
  private static final long DEFAULT_INTERVAL_SECONDS = 30;
  private final long intervalSeconds;

  private InfluxStatsConfig(long intervalSeconds) {
    this.intervalSeconds = intervalSeconds;
  }

  public static InfluxStatsConfig fromEnv() {
    String raw =
        System.getProperty(
            "INFLUXDB_STATS_INTERVAL_SECONDS",
            System.getenv("INFLUXDB_STATS_INTERVAL_SECONDS"));
    long interval = parseInterval(raw);
    return new InfluxStatsConfig(interval);
  }

  public long getIntervalSeconds() {
    return intervalSeconds;
  }

  private static long parseInterval(String raw) {
    if (raw == null || raw.isBlank()) {
      return DEFAULT_INTERVAL_SECONDS;
    }
    try {
      long value = Long.parseLong(raw.trim());
      return value > 0 ? value : DEFAULT_INTERVAL_SECONDS;
    } catch (NumberFormatException ex) {
      return DEFAULT_INTERVAL_SECONDS;
    }
  }
}

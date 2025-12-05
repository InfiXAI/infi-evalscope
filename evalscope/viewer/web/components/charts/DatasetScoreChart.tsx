"use client";

import ReactECharts from "echarts-for-react";

interface DatasetScore {
  dataset: string;
  score: number;
}

interface DatasetScoreChartProps {
  data: DatasetScore[];
  title?: string;
}

export function DatasetScoreChart({
  data,
  title = "Dataset Scores",
}: DatasetScoreChartProps) {
  const sortedData = [...data].sort((a, b) => b.score - a.score);

  const getColor = (score: number) => {
    if (score >= 0.8) return "#10B981"; // green
    if (score >= 0.6) return "#3B82F6"; // blue
    if (score >= 0.4) return "#F59E0B"; // yellow
    return "#EF4444"; // red
  };

  const option = {
    title: title
      ? {
          text: title,
          left: "center",
          textStyle: {
            fontSize: 14,
            fontWeight: 600,
            color: "#374151",
          },
        }
      : undefined,
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "shadow",
      },
      formatter: (params: { name: string; value: number }[]) => {
        if (params && params[0]) {
          return `${params[0].name}: ${(params[0].value * 100).toFixed(1)}%`;
        }
        return "";
      },
    },
    grid: {
      left: "3%",
      right: "10%",
      bottom: "3%",
      containLabel: true,
    },
    xAxis: {
      type: "value",
      max: 1,
      axisLabel: {
        formatter: (value: number) => `${(value * 100).toFixed(0)}%`,
      },
    },
    yAxis: {
      type: "category",
      data: sortedData.map((d) => d.dataset),
      axisLabel: {
        width: 100,
        overflow: "truncate",
        ellipsis: "...",
      },
    },
    series: [
      {
        type: "bar",
        data: sortedData.map((d) => ({
          value: d.score,
          itemStyle: {
            color: getColor(d.score),
            borderRadius: [0, 4, 4, 0],
          },
        })),
        label: {
          show: true,
          position: "right",
          formatter: (params: { value: number }) =>
            `${(params.value * 100).toFixed(1)}%`,
          fontSize: 12,
          color: "#6B7280",
        },
      },
    ],
  };

  return (
    <div className="w-full">
      <ReactECharts
        option={option}
        style={{ height: Math.max(200, data.length * 40) }}
        opts={{ renderer: "svg" }}
      />
    </div>
  );
}

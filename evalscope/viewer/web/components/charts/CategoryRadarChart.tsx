"use client";

import ReactECharts from "echarts-for-react";

interface CategoryScore {
  name: string;
  score: number;
}

interface CategoryRadarChartProps {
  data: CategoryScore[];
  title?: string;
}

export function CategoryRadarChart({
  data,
  title = "Category Breakdown",
}: CategoryRadarChartProps) {
  if (data.length < 3) {
    return (
      <div className="flex items-center justify-center h-[300px] text-gray-400">
        Not enough categories for radar chart (minimum 3)
      </div>
    );
  }

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
      trigger: "item",
    },
    radar: {
      indicator: data.map((d) => ({
        name: d.name,
        max: 1,
      })),
      shape: "polygon",
      splitNumber: 4,
      axisName: {
        color: "#6B7280",
        fontSize: 12,
      },
      splitLine: {
        lineStyle: {
          color: "#E5E7EB",
        },
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: ["#F9FAFB", "#F3F4F6", "#E5E7EB", "#D1D5DB"],
        },
      },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: data.map((d) => d.score),
            name: "Score",
            areaStyle: {
              color: "rgba(59, 130, 246, 0.3)",
            },
            lineStyle: {
              color: "#3B82F6",
              width: 2,
            },
            itemStyle: {
              color: "#3B82F6",
            },
          },
        ],
      },
    ],
  };

  return (
    <div className="w-full">
      <ReactECharts
        option={option}
        style={{ height: 300 }}
        opts={{ renderer: "svg" }}
      />
    </div>
  );
}

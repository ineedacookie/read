/**
 * Chart Builder Module
 * Centralized chart creation with consistent styling
 * Uses ECharts library
 * 
 * Usage:
 *   ChartBuilder.createLineChart('chartId', data, options);
 *   ChartBuilder.createPieChart('chartId', data, options);
 */

const ChartBuilder = {
    /**
     * Default chart options
     */
    defaultOptions: {
        animation: true,
        responsive: true,
        maintainAspectRatio: false,
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            top: '10%',
            containLabel: true
        }
    },
    
    /**
     * Create a line chart
     */
    createLineChart(elementId, data, customOptions = {}) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.error(`Element with id '${elementId}' not found`);
            return null;
        }
        
        const chart = echarts.init(element);
        
        const option = {
            ...this.defaultOptions,
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross'
                }
            },
            legend: {
                data: data.series.map(s => s.name),
                top: 0
            },
            xAxis: {
                type: 'category',
                data: data.labels,
                boundaryGap: false
            },
            yAxis: {
                type: 'value'
            },
            series: data.series.map(s => ({
                name: s.name,
                type: 'line',
                data: s.data,
                smooth: true,
                areaStyle: s.fill ? {} : null
            })),
            ...customOptions
        };
        
        chart.setOption(option);
        
        // Make responsive
        window.addEventListener('resize', () => chart.resize());
        
        return chart;
    },
    
    /**
     * Create a bar chart
     */
    createBarChart(elementId, data, customOptions = {}) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.error(`Element with id '${elementId}' not found`);
            return null;
        }
        
        const chart = echarts.init(element);
        
        const option = {
            ...this.defaultOptions,
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                }
            },
            legend: {
                data: data.series.map(s => s.name),
                top: 0
            },
            xAxis: {
                type: 'category',
                data: data.labels
            },
            yAxis: {
                type: 'value'
            },
            series: data.series.map(s => ({
                name: s.name,
                type: 'bar',
                data: s.data,
                barWidth: '60%'
            })),
            ...customOptions
        };
        
        chart.setOption(option);
        window.addEventListener('resize', () => chart.resize());
        
        return chart;
    },
    
    /**
     * Create a pie chart
     */
    createPieChart(elementId, data, customOptions = {}) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.error(`Element with id '${elementId}' not found`);
            return null;
        }
        
        const chart = echarts.init(element);
        
        const option = {
            ...this.defaultOptions,
            tooltip: {
                trigger: 'item',
                formatter: '{a} <br/>{b}: {c} ({d}%)'
            },
            legend: {
                orient: 'vertical',
                left: 'left',
                data: data.labels
            },
            series: [
                {
                    name: data.name || 'Data',
                    type: 'pie',
                    radius: ['40%', '70%'],
                    avoidLabelOverlap: false,
                    itemStyle: {
                        borderRadius: 10,
                        borderColor: '#fff',
                        borderWidth: 2
                    },
                    label: {
                        show: false,
                        position: 'center'
                    },
                    emphasis: {
                        label: {
                            show: true,
                            fontSize: 20,
                            fontWeight: 'bold'
                        }
                    },
                    labelLine: {
                        show: false
                    },
                    data: data.labels.map((label, index) => ({
                        name: label,
                        value: data.values[index]
                    }))
                }
            ],
            ...customOptions
        };
        
        chart.setOption(option);
        window.addEventListener('resize', () => chart.resize());
        
        return chart;
    },
    
    /**
     * Create a reading progress chart (specialized)
     */
    createReadingProgressChart(elementId, data, customOptions = {}) {
        const chartData = {
            labels: data.map(d => d.date || d.label),
            series: [
                {
                    name: 'Pages Read',
                    data: data.map(d => d.pages || 0),
                    fill: true
                },
                {
                    name: 'Minutes Read',
                    data: data.map(d => d.minutes || 0),
                    fill: false
                }
            ]
        };
        
        return this.createLineChart(elementId, chartData, {
            title: {
                text: 'Reading Progress',
                left: 'center'
            },
            ...customOptions
        });
    },
    
    /**
     * Create a goal progress chart
     */
    createGoalProgressChart(elementId, current, goal, customOptions = {}) {
        const percentage = goal > 0 ? (current / goal * 100).toFixed(1) : 0;
        
        const element = document.getElementById(elementId);
        if (!element) return null;
        
        const chart = echarts.init(element);
        
        const option = {
            series: [
                {
                    type: 'gauge',
                    startAngle: 180,
                    endAngle: 0,
                    min: 0,
                    max: 100,
                    splitNumber: 10,
                    progress: {
                        show: true,
                        width: 18
                    },
                    pointer: {
                        show: false
                    },
                    axisLine: {
                        lineStyle: {
                            width: 18
                        }
                    },
                    axisTick: {
                        show: false
                    },
                    splitLine: {
                        show: false
                    },
                    axisLabel: {
                        show: false
                    },
                    detail: {
                        valueAnimation: true,
                        formatter: '{value}%',
                        fontSize: 30,
                        offsetCenter: [0, '0%']
                    },
                    data: [
                        {
                            value: percentage
                        }
                    ]
                }
            ],
            ...customOptions
        };
        
        chart.setOption(option);
        window.addEventListener('resize', () => chart.resize());
        
        return chart;
    },
    
    /**
     * Update existing chart with new data
     */
    updateChart(chart, data) {
        if (!chart) return;
        
        chart.setOption({
            xAxis: {
                data: data.labels
            },
            series: data.series.map(s => ({
                data: s.data
            }))
        });
    },
    
    /**
     * Destroy chart instance
     */
    destroyChart(chart) {
        if (chart && typeof chart.dispose === 'function') {
            chart.dispose();
        }
    }
};

// Make available globally
if (typeof window !== 'undefined') {
    window.ChartBuilder = ChartBuilder;
}


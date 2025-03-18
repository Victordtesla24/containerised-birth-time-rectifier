// Function to fetch the initial chart data for more accurate question generation
  const fetchInitialChart = async ({
    birthDetails,
    setError,
    formatDateSafely,
    setChartData,
    sessionId,
    setSessionId
  }: {
    birthDetails: any;
    setError: (error: any) => void;
    formatDateSafely: (date: any, time?: any) => string;
    setChartData: (data: any) => void;
    sessionId: string | null;
    setSessionId: (id: string) => void;
  }) => {
    if (!birthDetails) return;
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      // Transform data to expected API format with proper date validation
      const apiPayload = {
        birthDate: formatDateSafely(
          birthDetails?.birthDate,
          birthDetails?.approximateTime
        ),
        birthTime: birthDetails?.approximateTime || '00:00:00',
        latitude: birthDetails?.coordinates?.latitude || 0,
        longitude: birthDetails?.coordinates?.longitude || 0,
        timezone: birthDetails?.timezone || 'UTC',
        chartType: 'all'
      };

      const response = await fetch(`${apiUrl}/api/v1/chart/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(apiPayload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        let errorMessage = `Failed to fetch initial chart data (Status: ${response.status})`;

        if (errorData?.detail) {
          if (Array.isArray(errorData.detail)) {
            // Format validation errors
            errorMessage = `Validation error: ${errorData.detail.map((err: any) => err.msg).join(', ')}`;
          } else {
            errorMessage = `Error: ${errorData.detail}`;
          }
        }

        throw new Error(errorMessage);
      }

      const data = await response.json();
      setChartData(data);

      // Generate a session ID if not already set
      if (!sessionId) {
        setSessionId(`session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`);
      }

      return data;
    } catch (error) {
      console.error('Error fetching initial chart:', error);
      setError(`Failed to initialize questionnaire: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return null;
    }
  };

// Gradio Client Utility to interface with the Seasonal Travel Recommender Space

// NOTE: You must install this package: npm install @gradio/client
// Import the 'client' function directly, as 'Client' is deprecated.
import { client } from "@gradio/client";

// Use the Vite environment variable for the Gradio Space URL
const GRADIO_SPACE_URL = import.meta.env.VITE_GRADIO_SPACE_URL || "http://localhost:8000";

let gradioClientInstance = null;

/**
 * Initializes and returns the Gradio Client instance (Singleton Pattern).
 * Uses the modern client() factory function instead of Client.connect().
 * @returns {Promise<ReturnType<typeof client>>} The initialized Gradio Client.
 */
const getGradioClient = async () => {
  // Check if the URL is set. The previous file assumed it was, but this is safer.
  if (!GRADIO_SPACE_URL) {
    throw new Error("VITE_GRADIO_SPACE_URL environment variable is not set.");
  }

  if (gradioClientInstance) {
    return gradioClientInstance;
  }

  try {
    console.log(`Connecting to Gradio Space: ${GRADIO_SPACE_URL}`);
    // Use the modern 'client()' factory function.
    // The client automatically handles connection and WebSocket setup.
    gradioClientInstance = await client(GRADIO_SPACE_URL);
    console.log("Gradio Client connected successfully.");
    return gradioClientInstance;
  } catch (error) {
    console.error("Failed to initialize Gradio Client:", error);
    gradioClientInstance = null;
    throw new Error("Could not connect to the Gradio Recommender service.");
  }
};

/**
 * Gets a travel recommendation from the Gradio model.
 * Assumes inputs are: [0] Season (string), [1] Interests (string).
 * * @param {string} season The season of travel.
 * @param {string} interests User's travel interests/preferences.
 * @returns {Promise<string>} The recommended travel destination/plan text.
 */
export const getTravelRecommendation = async (season, interests) => {
  try {
    const clientInstance = await getGradioClient();

    // The input array must match the order expected by the Gradio backend.
    const inputs = [season, interests];

    // Use the default "/predict" endpoint.
    const result = await clientInstance.predict("/predict", inputs);

    // We assume the first element of the data array is the recommendation string.
    const recommendation = result.data?.[0];

    if (typeof recommendation === "string") {
      return recommendation;
    } else {
      console.warn(
        "Gradio response did not contain a valid string recommendation.",
        result
      );
      throw new Error("Invalid response format from the recommender.");
    }
  } catch (error) {
    console.error("Error making prediction with Gradio client:", error);
    throw error;
  }
};

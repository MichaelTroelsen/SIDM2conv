import sw_emulator.software.SidId;
import java.io.*;

/**
 * Simple wrapper to test JC64's SidId player detection
 */
public class PlayerIdentifier {

    public static void main(String[] args) {
        if (args.length < 1) {
            System.out.println("Usage: java PlayerIdentifier <sid_file>");
            System.exit(1);
        }

        String sidFile = args[0];

        try {
            // Read SID file into buffer
            File file = new File(sidFile);
            FileInputStream fis = new FileInputStream(file);
            byte[] buffer = new byte[(int)file.length()];
            fis.read(buffer);
            fis.close();

            // Convert byte[] to int[] as required by SidId
            int[] intBuffer = new int[buffer.length];
            for (int i = 0; i < buffer.length; i++) {
                intBuffer[i] = buffer[i] & 0xFF;
            }

            // Get SidId instance
            SidId sidId = SidId.instance;

            // Identify player
            String players = sidId.identifyBuffer(intBuffer, intBuffer.length);

            if (players != null && !players.isEmpty()) {
                System.out.println("Detected player: " + players);
            } else {
                System.out.println("Unknown player (no match found)");
            }

            // Show statistics
            System.out.println("Total players in database: " + sidId.getNumberOfPlayers());
            System.out.println("Total patterns: " + sidId.getNumberOfPatterns());

        } catch (IOException e) {
            System.err.println("Error reading file: " + e.getMessage());
            System.exit(1);
        } catch (Exception e) {
            System.err.println("Error during detection: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
}

import java.io.BufferedReader;
import java.io.InputStreamReader;


public class JavaDriver {
    public static void main(String[] args) {
        try {
            BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
            Solution bot = new Solution();

            String line;
            while ((line = reader.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty()) continue;
                if (line.equals("QUIT")) break;

                try {
                    String moveJson = bot.getMove(line);
                    
                    if (moveJson == null || moveJson.isEmpty()) {
                        System.out.println("__CRASH__");
                    } else {
                        System.out.println(moveJson);
                    }
                    System.out.flush();
                } catch (Exception e) {
                    System.err.println("RUNTIME_ERROR: " + e.getMessage());
                    System.out.println("__CRASH__");
                    System.out.flush();
                }
            }
        } catch (Exception e) {
            System.exit(1);
        }
    }
}
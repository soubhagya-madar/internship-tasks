class Student {
    private String name = "Soubhagya";

    public void display() {
        System.out.println("Student name: " + name);
    }

    public static void main(String[] args) {
        Student s = new Student();
        s.display();
    }
}
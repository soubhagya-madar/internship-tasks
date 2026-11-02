class Animal {
    void sound() {
        System.out.println("Animal makes a sound");
    }
}

class Dog extends Animal {
    void sound() {
        System.out.println("Dog barks");
    }
}

class Polymorphism {
    public static void main(String[] args) {
        Animal a = new Dog();
        a.sound();
    }
}